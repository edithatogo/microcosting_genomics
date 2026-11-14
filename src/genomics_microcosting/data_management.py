# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Data management system for microcosting analysis."""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from .logging_config import get_logger

logger = get_logger(__name__)


class DataVersion:
    """Represents a version of a dataset."""

    def __init__(
        self,
        version_id: str,
        timestamp: datetime,
        file_path: Path,
        checksum: str,
        metadata: dict[str, Any],
    ) -> None:
        """Initialize a DataVersion.

        Args:
            version_id (str): Unique identifier for this version
            timestamp (datetime): When this version was created
            file_path (Path): Path to the data file
            checksum (str): Checksum of the file content
            metadata (Dict[str, Any]): Additional metadata about the version

        """
        self.version_id = version_id
        self.timestamp = timestamp
        self.file_path = file_path
        self.checksum = checksum
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dict[str, Any]: Dictionary representation

        """
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "file_path": str(self.file_path),
            "checksum": self.checksum,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataVersion:
        """Create DataVersion from dictionary.

        Args:
            data (Dict[str, Any]): Dictionary representation

        Returns:
            DataVersion: Created DataVersion instance

        """
        return cls(
            version_id=data["version_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            file_path=Path(data["file_path"]),
            checksum=data["checksum"],
            metadata=data["metadata"],
        )


class DataManager:
    """Manages data versions, lineage, and metadata."""

    def __init__(
        self,
        data_directory: Path,
        metadata_directory: Path | None = None,
    ) -> None:
        """Initialize the DataManager.

        Args:
            data_directory (Path): Directory containing data files
            metadata_directory (Path, optional): Directory for metadata files

        """
        self.data_directory = Path(data_directory)
        self.metadata_directory = (
            Path(metadata_directory)
            if metadata_directory
            else self.data_directory / "metadata"
        )
        self.metadata_directory.mkdir(exist_ok=True)

        # Load existing metadata
        self.datasets: dict[str, list[DataVersion]] = {}
        self._load_metadata()

        logger.info(
            "DataManager initialized with data directory: %s",
            self.data_directory,
        )
        logger.info("Metadata directory: %s", self.metadata_directory)

    def _get_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path (Path): Path to the file

        Returns:
            str: SHA256 checksum

        """
        hash_sha256 = hashlib.sha256()
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _get_dataset_name(self, file_path: Path) -> str:
        """Get dataset name from file path.

        Args:
            file_path (Path): Path to the file

        Returns:
            str: Dataset name

        """
        return file_path.stem

    def _load_metadata(self) -> None:
        """Load existing metadata from files."""
        metadata_file = self.metadata_directory / "datasets.json"
        if metadata_file.exists():
            try:
                with Path(metadata_file).open() as f:
                    data = json.load(f)

                for dataset_name, versions_data in data.items():
                    versions = [
                        DataVersion.from_dict(version_data)
                        for version_data in versions_data
                    ]
                    self.datasets[dataset_name] = versions

                logger.info("Loaded metadata for %s datasets", len(self.datasets))
            except Exception:
                logger.exception("Error loading metadata")

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        metadata_file = self.metadata_directory / "datasets.json"
        try:
            data = {}
            for dataset_name, versions in self.datasets.items():
                data[dataset_name] = [version.to_dict() for version in versions]

            with Path(metadata_file).open("w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved metadata for %s datasets", len(self.datasets))
        except Exception:
            logger.exception("Error saving metadata")

    def register_dataset(
        self,
        file_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Register a dataset file and create a new version.

        Args:
            file_path (Path): Path to the dataset file
            metadata (Dict[str, Any], optional): Additional metadata

        Returns:
            str: Version ID of the registered dataset

        """
        if not file_path.exists():
            message = f"Dataset file not found: {file_path}"
            raise FileNotFoundError(message)

        dataset_name = self._get_dataset_name(file_path)
        checksum = self._get_file_checksum(file_path)
        timestamp = datetime.now(UTC).astimezone()
        version_id = f"{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Create metadata
        file_metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "created_by": "DataManager",
        }
        if metadata:
            file_metadata.update(metadata)

        # Create version
        version = DataVersion(
            version_id=version_id,
            timestamp=timestamp,
            file_path=file_path,
            checksum=checksum,
            metadata=file_metadata,
        )

        # Add to datasets
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = []
        self.datasets[dataset_name].append(version)

        # Save metadata
        self._save_metadata()

        logger.info("Registered dataset %s with version %s", dataset_name, version_id)
        return version_id

    def get_dataset_versions(self, dataset_name: str) -> list[DataVersion]:
        """Get all versions of a dataset.

        Args:
            dataset_name (str): Name of the dataset

        Returns:
            List[DataVersion]: List of versions

        """
        return self.datasets.get(dataset_name, [])

    def get_latest_version(self, dataset_name: str) -> DataVersion | None:
        """Get the latest version of a dataset.

        Args:
            dataset_name (str): Name of the dataset

        Returns:
            DataVersion: Latest version, or None if dataset not found

        """
        versions = self.get_dataset_versions(dataset_name)
        if not versions:
            return None
        return max(versions, key=lambda v: v.timestamp.astimezone(UTC))

    def load_dataset(
        self,
        dataset_name: str,
        version_id: str | None = None,
        *,
        schema_overrides: dict[str, pl.DataType] | None = None,
    ) -> pl.DataFrame:
        """Load a dataset.

        Args:
            dataset_name (str): Name of the dataset
            version_id (str, optional): Specific version to load
            schema_overrides: Required column types for CSV versions

        Returns:
            pl.DataFrame: Loaded dataset

        """
        if version_id:
            # Find specific version
            versions = self.get_dataset_versions(dataset_name)
            version = next((v for v in versions if v.version_id == version_id), None)
            if not version:
                message = f"Version {version_id} not found for dataset {dataset_name}"
                raise ValueError(
                    message,
                )
        else:
            # Get latest version
            version = self.get_latest_version(dataset_name)
            if not version:
                message = f"Dataset {dataset_name} not found"
                raise ValueError(message)

        # Load the data
        file_path = version.file_path
        if not file_path.exists():
            message = f"Data file not found: {file_path}"
            raise FileNotFoundError(message)

        logger.info("Loading dataset %s version %s", dataset_name, version.version_id)

        # Load based on file extension
        if file_path.suffix.lower() == ".parquet":
            return pl.read_parquet(file_path)
        if file_path.suffix.lower() == ".csv":
            return pl.read_csv(
                file_path,
                infer_schema=False,
                schema_overrides=schema_overrides,
            )
        message = f"Unsupported file format: {file_path.suffix}"
        raise ValueError(message)

    def get_dataset_info(self, dataset_name: str) -> dict[str, Any]:
        """Get information about a dataset.

        Args:
            dataset_name (str): Name of the dataset

        Returns:
            Dict[str, Any]: Dataset information

        """
        versions = self.get_dataset_versions(dataset_name)
        if not versions:
            return {"error": f"Dataset {dataset_name} not found"}

        latest_version = self.get_latest_version(dataset_name)

        # Load dataset to get statistics
        try:
            df = self.load_dataset(dataset_name)
            info = {
                "dataset_name": dataset_name,
                "version_count": len(versions),
                "latest_version": latest_version.version_id if latest_version else None,
                "latest_timestamp": latest_version.timestamp.isoformat()
                if latest_version
                else None,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.schema.items()},
                "memory_usage": df.estimated_size(),
            }
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            pl.exceptions.PolarsError,
        ) as e:
            info = {
                "dataset_name": dataset_name,
                "version_count": len(versions),
                "latest_version": latest_version.version_id if latest_version else None,
                "latest_timestamp": latest_version.timestamp.isoformat()
                if latest_version
                else None,
                "error": f"Error loading dataset: {e}",
            }

        return info

    def list_datasets(self) -> list[str]:
        """List all registered datasets.

        Returns:
            List[str]: List of dataset names

        """
        return list(self.datasets.keys())

    def verify_integrity(
        self,
        dataset_name: str,
        version_id: str | None = None,
    ) -> bool:
        """Verify the integrity of a dataset version.

        Args:
            dataset_name (str): Name of the dataset
            version_id (str, optional): Specific version to verify

        Returns:
            bool: True if integrity is verified, False otherwise

        """
        if version_id:
            # Find specific version
            versions = self.get_dataset_versions(dataset_name)
            version = next((v for v in versions if v.version_id == version_id), None)
            if not version:
                message = f"Version {version_id} not found for dataset {dataset_name}"
                raise ValueError(
                    message,
                )
        else:
            # Get latest version
            version = self.get_latest_version(dataset_name)
            if not version:
                message = f"Dataset {dataset_name} not found"
                raise ValueError(message)

        # Check if file exists
        if not version.file_path.exists():
            logger.error("File not found: %s", version.file_path)
            return False

        # Calculate checksum and compare
        current_checksum = self._get_file_checksum(version.file_path)
        if current_checksum != version.checksum:
            logger.error(
                "Checksum mismatch for %s version %s",
                dataset_name,
                version.version_id,
            )
            return False

        logger.info(
            "Integrity verified for %s version %s",
            dataset_name,
            version.version_id,
        )
        return True


# Example usage function
def example_usage() -> None:
    """Demonstrate the data management system."""
    logger.info("%s", "Data Management System Example")

    # Initialize data manager
    data_dir = Path(__file__).resolve().parents[2] / "data" / "prepared"
    metadata_dir = Path(__file__).resolve().parents[2] / "data" / "metadata"

    dm = DataManager(data_dir, metadata_dir)

    # Register some datasets
    parquet_files = list(data_dir.glob("*.parquet"))
    for file_path in parquet_files[:3]:  # Register first 3 files
        try:
            version_id = dm.register_dataset(
                file_path,
                metadata={
                    "source": "microcosting_project",
                    "description": f"Dataset {file_path.stem}",
                },
            )
            logger.info("%s", f"Registered {file_path.name} with version {version_id}")
        except OSError, ValueError, TypeError:
            logger.warning("Error registering %s", file_path.name, exc_info=True)

    # List datasets
    datasets = dm.list_datasets()
    logger.info("%s", f"\nRegistered datasets: {datasets}")

    # Get dataset info
    if datasets:
        info = dm.get_dataset_info(datasets[0])
        logger.info("%s", f"\nDataset info for {datasets[0]}:")
        for key, value in info.items():
            logger.info("%s", f"  {key}: {value}")

    # Load a dataset
    if datasets:
        try:
            df = dm.load_dataset(datasets[0])
            logger.info("%s", f"\nLoaded dataset {datasets[0]} with shape {df.shape}")
            logger.info("%s", df.head())
        except OSError, ValueError, KeyError, TypeError, pl.exceptions.PolarsError:
            logger.warning("Error loading dataset", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
