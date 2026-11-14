# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Version control system for Excel workbooks."""

import hashlib
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import polars as pl
from openpyxl import Workbook

from .logging_config import get_logger

logger = get_logger(__name__)


class WorkbookVersion:
    """Represents a version of an Excel workbook."""

    def __init__(
        self,
        version_id: str,
        timestamp: datetime,
        file_path: Path,
        checksum: str,
        metadata: dict[str, Any],
    ) -> None:
        """Initialize a WorkbookVersion.

        Args:
            version_id (str): Unique identifier for this version
            timestamp (datetime): When this version was created
            file_path (Path): Path to the workbook file
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
    def from_dict(cls, data: dict[str, Any]) -> WorkbookVersion:
        """Create WorkbookVersion from dictionary.

        Args:
            data (Dict[str, Any]): Dictionary representation

        Returns:
            WorkbookVersion: Created WorkbookVersion instance

        """
        return cls(
            version_id=data["version_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            file_path=Path(data["file_path"]),
            checksum=data["checksum"],
            metadata=data["metadata"],
        )


class WorkbookVersionControl:
    """Manages version control for Excel workbooks."""

    def __init__(self, repository_directory: Path) -> None:
        """Initialize the workbook version control system.

        Args:
            repository_directory (Path): Directory to store workbook versions

        """
        self.repository_directory = Path(repository_directory)
        self.repository_directory.mkdir(exist_ok=True)

        # Create subdirectories
        self.workbooks_dir = self.repository_directory / "workbooks"
        self.metadata_dir = self.repository_directory / "metadata"
        self.workbooks_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)

        # Load existing metadata
        self.workbooks: dict[str, list[WorkbookVersion]] = {}
        self._load_metadata()

        logger.info(
            "WorkbookVersionControl initialized with repository: %s",
            self.repository_directory,
        )

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

    def _get_workbook_name(self, file_path: Path) -> str:
        """Get workbook name from file path.

        Args:
            file_path (Path): Path to the file

        Returns:
            str: Workbook name

        """
        return file_path.stem

    def _load_metadata(self) -> None:
        """Load existing metadata from files."""
        metadata_file = self.metadata_dir / "workbooks.json"
        if metadata_file.exists():
            try:
                with Path(metadata_file).open() as f:
                    data = json.load(f)

                for workbook_name, versions_data in data.items():
                    versions = [
                        WorkbookVersion.from_dict(version_data)
                        for version_data in versions_data
                    ]
                    self.workbooks[workbook_name] = versions

                logger.info("Loaded metadata for %s workbooks", len(self.workbooks))
            except Exception:
                logger.exception("Error loading metadata")

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        metadata_file = self.metadata_dir / "workbooks.json"
        try:
            data = {}
            for workbook_name, versions in self.workbooks.items():
                data[workbook_name] = [version.to_dict() for version in versions]

            with Path(metadata_file).open("w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved metadata for %s workbooks", len(self.workbooks))
        except Exception:
            logger.exception("Error saving metadata")

    def commit_workbook(
        self,
        file_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Commit a workbook file and create a new version.

        Args:
            file_path (Path): Path to the workbook file
            metadata (Dict[str, Any], optional): Additional metadata

        Returns:
            str: Version ID of the committed workbook

        Raises:
            FileNotFoundError: If the workbook file is not found

        """
        if not file_path.exists():
            message = f"Workbook file not found: {file_path}"
            raise FileNotFoundError(message)

        workbook_name = self._get_workbook_name(file_path)
        checksum = self._get_file_checksum(file_path)
        timestamp = datetime.now(UTC).astimezone()
        version_id = f"{workbook_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Check if this is the same as the latest version
        latest_version = self.get_latest_version(workbook_name)
        if latest_version and latest_version.checksum == checksum:
            logger.info("Workbook %s unchanged since last commit", workbook_name)
            return latest_version.version_id

        # Copy file to repository
        repo_file_path = self.workbooks_dir / f"{version_id}{file_path.suffix}"
        shutil.copy2(file_path, repo_file_path)

        # Create metadata
        file_metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "original_path": str(file_path),
            "committed_by": "WorkbookVersionControl",
        }
        if metadata:
            file_metadata.update(metadata)

        # Create version
        version = WorkbookVersion(
            version_id=version_id,
            timestamp=timestamp,
            file_path=repo_file_path,
            checksum=checksum,
            metadata=file_metadata,
        )

        # Add to workbooks
        if workbook_name not in self.workbooks:
            self.workbooks[workbook_name] = []
        self.workbooks[workbook_name].append(version)

        # Save metadata
        self._save_metadata()

        logger.info("Committed workbook %s with version %s", workbook_name, version_id)
        return version_id

    def get_workbook_versions(self, workbook_name: str) -> list[WorkbookVersion]:
        """Get all versions of a workbook.

        Args:
            workbook_name (str): Name of the workbook

        Returns:
            List[WorkbookVersion]: List of versions

        """
        return self.workbooks.get(workbook_name, [])

    def get_latest_version(self, workbook_name: str) -> WorkbookVersion | None:
        """Get the latest version of a workbook.

        Args:
            workbook_name (str): Name of the workbook

        Returns:
            WorkbookVersion: Latest version, or None if workbook not found

        """
        versions = self.get_workbook_versions(workbook_name)
        if not versions:
            return None
        return max(versions, key=lambda v: v.timestamp.astimezone(UTC))

    def checkout_workbook(
        self,
        workbook_name: str,
        version_id: str | None = None,
        output_path: Path | None = None,
    ) -> Path:
        """Checkout a workbook version.

        Args:
            workbook_name (str): Name of the workbook
            version_id (str, optional): Specific version to checkout
            output_path (Path, optional): Path to save the checked out file

        Returns:
            Path: Path to the checked out file

        Raises:
            ValueError: If workbook or version not found
            FileNotFoundError: If the stored file is missing

        """
        if version_id:
            # Find specific version
            versions = self.get_workbook_versions(workbook_name)
            version = next((v for v in versions if v.version_id == version_id), None)
            if not version:
                message = f"Version {version_id} not found for workbook {workbook_name}"
                raise ValueError(
                    message,
                )
        else:
            # Get latest version
            version = self.get_latest_version(workbook_name)
            if not version:
                message = f"Workbook {workbook_name} not found"
                raise ValueError(message)

        # Check if stored file exists
        if not version.file_path.exists():
            message = f"Stored workbook file not found: {version.file_path}"
            raise FileNotFoundError(
                message,
            )

        # Determine output path
        if output_path is None:
            output_path = Path.cwd() / f"{workbook_name}{version.file_path.suffix}"

        # Copy file to output path
        shutil.copy2(version.file_path, output_path)

        logger.info(
            "Checked out workbook %s version %s to %s",
            workbook_name,
            version.version_id,
            output_path,
        )
        return output_path

    def get_workbook_info(self, workbook_name: str) -> dict[str, Any]:
        """Get information about a workbook.

        Args:
            workbook_name (str): Name of the workbook

        Returns:
            Dict[str, Any]: Workbook information

        """
        versions = self.get_workbook_versions(workbook_name)
        if not versions:
            return {"error": f"Workbook {workbook_name} not found"}

        latest_version = self.get_latest_version(workbook_name)

        return {
            "workbook_name": workbook_name,
            "version_count": len(versions),
            "latest_version": latest_version.version_id if latest_version else None,
            "latest_timestamp": latest_version.timestamp.isoformat()
            if latest_version
            else None,
            "file_extension": latest_version.file_path.suffix
            if latest_version
            else None,
            "file_size": latest_version.metadata.get("file_size")
            if latest_version
            else None,
        }

    def list_workbooks(self) -> list[str]:
        """List all tracked workbooks.

        Returns:
            List[str]: List of workbook names

        """
        return list(self.workbooks.keys())

    def compare_versions(
        self,
        workbook_name: str,
        version_id1: str,
        version_id2: str,
    ) -> dict[str, Any]:
        """Compare two versions of a workbook.

        Args:
            workbook_name (str): Name of the workbook
            version_id1 (str): First version ID
            version_id2 (str): Second version ID

        Returns:
            Dict[str, Any]: Comparison results

        """
        # Get both versions
        versions = self.get_workbook_versions(workbook_name)
        version1 = next((v for v in versions if v.version_id == version_id1), None)
        version2 = next((v for v in versions if v.version_id == version_id2), None)

        if not version1:
            message = f"Version {version_id1} not found for workbook {workbook_name}"
            raise ValueError(
                message,
            )
        if not version2:
            message = f"Version {version_id2} not found for workbook {workbook_name}"
            raise ValueError(
                message,
            )

        comparison = {
            "workbook_name": workbook_name,
            "version1": version_id1,
            "version2": version_id2,
            "version1_timestamp": version1.timestamp.isoformat(),
            "version2_timestamp": version2.timestamp.isoformat(),
            "same_checksum": version1.checksum == version2.checksum,
            "version1_size": version1.metadata.get("file_size"),
            "version2_size": version2.metadata.get("file_size"),
        }

        # If files are different, try to compare sheet structure
        if version1.checksum != version2.checksum:
            try:
                # This is a simplified comparison - in a real implementation,
                # we would compare the actual content of the Excel files
                comparison["differences"] = {
                    "file_size_change": (
                        version2.metadata.get("file_size", 0)
                        - version1.metadata.get("file_size", 0)
                    ),
                }
            except (TypeError, ValueError) as e:
                comparison["comparison_error"] = str(e)

        return comparison

    def verify_integrity(
        self,
        workbook_name: str,
        version_id: str | None = None,
    ) -> bool:
        """Verify the integrity of a workbook version.

        Args:
            workbook_name (str): Name of the workbook
            version_id (str, optional): Specific version to verify

        Returns:
            bool: True if integrity is verified, False otherwise

        """
        if version_id:
            # Find specific version
            versions = self.get_workbook_versions(workbook_name)
            version = next((v for v in versions if v.version_id == version_id), None)
            if not version:
                message = f"Version {version_id} not found for workbook {workbook_name}"
                raise ValueError(
                    message,
                )
        else:
            # Get latest version
            version = self.get_latest_version(workbook_name)
            if not version:
                message = f"Workbook {workbook_name} not found"
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
                workbook_name,
                version_id,
            )
            return False

        logger.info("Integrity verified for %s version %s", workbook_name, version_id)
        return True


# Example usage function
def example_usage() -> None:
    """Demonstrate the workbook version control system."""
    logger.info("%s", "Workbook Version Control System Example")

    # Initialize version control
    repo_dir = Path(__file__).resolve().parent / "workbook_repo"
    vc = WorkbookVersionControl(repo_dir)

    # For demonstration, let's create a simple Excel file
    with TemporaryDirectory(prefix="microcosting-workbook-") as directory:
        # Create a simple DataFrame and save as Excel
        df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        book = Workbook()
        sheet = book["Sheet"]
        sheet.append(df.columns)
        for row in df.iter_rows():
            sheet.append(row)
        workbook_path = Path(directory) / "example.xlsx"
        book.save(workbook_path)

        # Commit the workbook
        version_id = vc.commit_workbook(
            workbook_path,
            metadata={"author": "example_user", "description": "Example workbook"},
        )
        logger.info("%s", f"Committed workbook with version {version_id}")

        # List workbooks
        workbooks = vc.list_workbooks()
        logger.info("%s", f"Tracked workbooks: {workbooks}")

        # Get workbook info
        if workbooks:
            info = vc.get_workbook_info(workbooks[0])
            logger.info("%s", f"Workbook info: {info}")

    logger.info("%s", "Example completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
