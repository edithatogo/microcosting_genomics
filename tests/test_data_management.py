"""Tests for the data management system."""

import pandas as pd
import pytest
from pathlib import Path
import tempfile
import shutil

from unimelb_phd_phase_1.data_management import DataManager, DataVersion


def test_data_version_creation():
    """Test creating a DataVersion."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "test.csv"
        temp_path.write_text("a,b\n1,2\n3,4")
        
        version = DataVersion(
            version_id="test_v1",
            timestamp=pd.Timestamp.now(),
            file_path=temp_path,
            checksum="test_checksum",
            metadata={"source": "test"}
        )
        
        assert version.version_id == "test_v1"
        assert version.file_path == temp_path
        assert version.checksum == "test_checksum"
        assert version.metadata == {"source": "test"}
        
        # Test serialization
        version_dict = version.to_dict()
        restored_version = DataVersion.from_dict(version_dict)
        
        assert restored_version.version_id == version.version_id
        assert restored_version.file_path == version.file_path
        assert restored_version.checksum == version.checksum
        assert restored_version.metadata == version.metadata


def test_data_manager_initialization():
    """Test initializing DataManager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        dm = DataManager(data_dir, metadata_dir)
        
        assert dm.data_directory == data_dir
        assert dm.metadata_directory == metadata_dir


def test_data_manager_register_dataset():
    """Test registering a dataset."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.to_csv(test_file, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        version_id = dm.register_dataset(test_file, {"description": "Test data"})
        
        assert version_id is not None
        assert "test_data" in dm.datasets
        assert len(dm.datasets["test_data"]) == 1
        
        version = dm.datasets["test_data"][0]
        assert version.version_id.startswith("test_data_")
        assert version.metadata["description"] == "Test data"


def test_data_manager_list_datasets():
    """Test listing datasets."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create test data files
        test_file1 = data_dir / "test_data1.csv"
        test_file2 = data_dir / "test_data2.csv"
        pd.DataFrame({"a": [1, 2]}).to_csv(test_file1, index=False)
        pd.DataFrame({"b": [3, 4]}).to_csv(test_file2, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file1)
        dm.register_dataset(test_file2)
        
        datasets = dm.list_datasets()
        assert len(datasets) == 2
        assert "test_data1" in datasets
        assert "test_data2" in datasets


def test_data_manager_get_dataset_info():
    """Test getting dataset info."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.to_csv(test_file, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)
        
        info = dm.get_dataset_info("test_data")
        assert info["dataset_name"] == "test_data"
        assert info["version_count"] == 1
        assert info["row_count"] == 3
        assert info["column_count"] == 2
        assert "a" in info["columns"]
        assert "b" in info["columns"]


def test_data_manager_load_dataset():
    """Test loading a dataset."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create test data file
        test_file = data_dir / "test_data.csv"
        original_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        original_data.to_csv(test_file, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)
        
        # Load the dataset
        loaded_data = dm.load_dataset("test_data")
        
        # Check that data is the same
        pd.testing.assert_frame_equal(original_data, loaded_data)


def test_data_manager_verify_integrity():
    """Test verifying dataset integrity."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.to_csv(test_file, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)
        
        # Verify integrity
        is_valid = dm.verify_integrity("test_data")
        assert is_valid
        
        # Modify file and verify it fails
        with open(test_file, "a") as f:
            f.write("7,8\n")
            
        is_valid = dm.verify_integrity("test_data")
        assert not is_valid


def test_data_manager_multiple_versions():
    """Test handling multiple versions of a dataset."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"
        
        data_dir.mkdir()
        metadata_dir.mkdir()
        
        # Create initial test data file
        test_file = data_dir / "test_data.csv"
        test_data_v1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        test_data_v1.to_csv(test_file, index=False)
        
        dm = DataManager(data_dir, metadata_dir)
        version_id_1 = dm.register_dataset(test_file, {"version": "v1"})
        
        # Modify data and register again
        test_data_v2 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data_v2.to_csv(test_file, index=False)
        version_id_2 = dm.register_dataset(test_file, {"version": "v2"})
        
        # Check versions
        versions = dm.get_dataset_versions("test_data")
        assert len(versions) == 2
        
        # Check latest version
        latest = dm.get_latest_version("test_data")
        assert latest.version_id == version_id_2
        
        # Load data (will load current file content)
        data_current = dm.load_dataset("test_data")
        assert len(data_current) == 3  # Current content has 3 rows


if __name__ == "__main__":
    pytest.main([__file__])