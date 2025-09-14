"""Data management system for microcosting analysis."""

import pandas as pd
from pathlib import Path
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from .logging_config import get_logger


logger = get_logger(__name__)


class DataVersion:
    """Represents a version of a dataset."""
    
    def __init__(self, version_id: str, timestamp: datetime, file_path: Path, 
                 checksum: str, metadata: Dict[str, Any]):
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "file_path": str(self.file_path),
            "checksum": self.checksum,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataVersion':
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
            metadata=data["metadata"]
        )


class DataManager:
    """Manages data versions, lineage, and metadata."""
    
    def __init__(self, data_directory: Path, metadata_directory: Optional[Path] = None):
        """Initialize the DataManager.
        
        Args:
            data_directory (Path): Directory containing data files
            metadata_directory (Path, optional): Directory for metadata files
        """
        self.data_directory = Path(data_directory)
        self.metadata_directory = Path(metadata_directory) if metadata_directory else self.data_directory / "metadata"
        self.metadata_directory.mkdir(exist_ok=True)
        
        # Load existing metadata
        self.datasets: Dict[str, List[DataVersion]] = {}
        self._load_metadata()
        
        logger.info(f"DataManager initialized with data directory: {self.data_directory}")
        logger.info(f"Metadata directory: {self.metadata_directory}")
    
    def _get_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            str: SHA256 checksum
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
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
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                
                for dataset_name, versions_data in data.items():
                    versions = [DataVersion.from_dict(version_data) for version_data in versions_data]
                    self.datasets[dataset_name] = versions
                    
                logger.info(f"Loaded metadata for {len(self.datasets)} datasets")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")
    
    def _save_metadata(self) -> None:
        """Save metadata to file."""
        metadata_file = self.metadata_directory / "datasets.json"
        try:
            data = {}
            for dataset_name, versions in self.datasets.items():
                data[dataset_name] = [version.to_dict() for version in versions]
            
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved metadata for {len(self.datasets)} datasets")
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def register_dataset(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Register a dataset file and create a new version.
        
        Args:
            file_path (Path): Path to the dataset file
            metadata (Dict[str, Any], optional): Additional metadata
            
        Returns:
            str: Version ID of the registered dataset
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        dataset_name = self._get_dataset_name(file_path)
        checksum = self._get_file_checksum(file_path)
        timestamp = datetime.now()
        version_id = f"{dataset_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Create metadata
        file_metadata = {
            "file_size": file_path.stat().st_size,
            "file_extension": file_path.suffix,
            "created_by": "DataManager"
        }
        if metadata:
            file_metadata.update(metadata)
        
        # Create version
        version = DataVersion(
            version_id=version_id,
            timestamp=timestamp,
            file_path=file_path,
            checksum=checksum,
            metadata=file_metadata
        )
        
        # Add to datasets
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = []
        self.datasets[dataset_name].append(version)
        
        # Save metadata
        self._save_metadata()
        
        logger.info(f"Registered dataset {dataset_name} with version {version_id}")
        return version_id
    
    def get_dataset_versions(self, dataset_name: str) -> List[DataVersion]:
        """Get all versions of a dataset.
        
        Args:
            dataset_name (str): Name of the dataset
            
        Returns:
            List[DataVersion]: List of versions
        """
        return self.datasets.get(dataset_name, [])
    
    def get_latest_version(self, dataset_name: str) -> Optional[DataVersion]:
        """Get the latest version of a dataset.
        
        Args:
            dataset_name (str): Name of the dataset
            
        Returns:
            DataVersion: Latest version, or None if dataset not found
        """
        versions = self.get_dataset_versions(dataset_name)
        if not versions:
            return None
        return sorted(versions, key=lambda v: v.timestamp, reverse=True)[0]
    
    def load_dataset(self, dataset_name: str, version_id: Optional[str] = None) -> pd.DataFrame:
        """Load a dataset.
        
        Args:
            dataset_name (str): Name of the dataset
            version_id (str, optional): Specific version to load
            
        Returns:
            pd.DataFrame: Loaded dataset
        """
        if version_id:
            # Find specific version
            versions = self.get_dataset_versions(dataset_name)
            version = next((v for v in versions if v.version_id == version_id), None)
            if not version:
                raise ValueError(f"Version {version_id} not found for dataset {dataset_name}")
        else:
            # Get latest version
            version = self.get_latest_version(dataset_name)
            if not version:
                raise ValueError(f"Dataset {dataset_name} not found")
        
        # Load the data
        file_path = version.file_path
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        logger.info(f"Loading dataset {dataset_name} version {version.version_id}")
        
        # Load based on file extension
        if file_path.suffix.lower() == '.parquet':
            return pd.read_parquet(file_path)
        elif file_path.suffix.lower() == '.csv':
            return pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
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
                "latest_timestamp": latest_version.timestamp.isoformat() if latest_version else None,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "data_types": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_usage": df.memory_usage(deep=True).sum()
            }
        except Exception as e:
            info = {
                "dataset_name": dataset_name,
                "version_count": len(versions),
                "latest_version": latest_version.version_id if latest_version else None,
                "latest_timestamp": latest_version.timestamp.isoformat() if latest_version else None,
                "error": f"Error loading dataset: {e}"
            }
        
        return info
    
    def list_datasets(self) -> List[str]:
        """List all registered datasets.
        
        Returns:
            List[str]: List of dataset names
        """
        return list(self.datasets.keys())
    
    def verify_integrity(self, dataset_name: str, version_id: Optional[str] = None) -> bool:
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
                raise ValueError(f"Version {version_id} not found for dataset {dataset_name}")
        else:
            # Get latest version
            version = self.get_latest_version(dataset_name)
            if not version:
                raise ValueError(f"Dataset {dataset_name} not found")
        
        # Check if file exists
        if not version.file_path.exists():
            logger.error(f"File not found: {version.file_path}")
            return False
        
        # Calculate checksum and compare
        current_checksum = self._get_file_checksum(version.file_path)
        if current_checksum != version.checksum:
            logger.error(f"Checksum mismatch for {dataset_name} version {version.version_id}")
            return False
        
        logger.info(f"Integrity verified for {dataset_name} version {version.version_id}")
        return True


# Example usage function
def example_usage():
    """Example of how to use the data management system."""
    print("Data Management System Example")
    
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
                metadata={"source": "microcosting_project", "description": f"Dataset {file_path.stem}"}
            )
            print(f"Registered {file_path.name} with version {version_id}")
        except Exception as e:
            print(f"Error registering {file_path.name}: {e}")
    
    # List datasets
    datasets = dm.list_datasets()
    print(f"\nRegistered datasets: {datasets}")
    
    # Get dataset info
    if datasets:
        info = dm.get_dataset_info(datasets[0])
        print(f"\nDataset info for {datasets[0]}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    # Load a dataset
    if datasets:
        try:
            df = dm.load_dataset(datasets[0])
            print(f"\nLoaded dataset {datasets[0]} with shape {df.shape}")
            print(df.head())
        except Exception as e:
            print(f"Error loading dataset: {e}")


if __name__ == "__main__":
    example_usage()