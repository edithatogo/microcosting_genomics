# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for the data management system."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from genomics_microcosting.data_management import DataManager, DataVersion
from tests.checks import require_equal, require_runtime_instance


def test_data_version_creation() -> None:
    """Test creating a DataVersion."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "test.csv"
        temp_path.write_text("a,b\n1,2\n3,4")

        version = DataVersion(
            version_id="test_v1",
            timestamp=datetime.now(UTC).astimezone(),
            file_path=temp_path,
            checksum="test_checksum",
            metadata={"source": "test"},
        )

        if not (version.version_id == "test_v1"):
            raise AssertionError
        if not (version.file_path == temp_path):
            raise AssertionError
        if not (version.checksum == "test_checksum"):
            raise AssertionError
        if not (version.metadata == {"source": "test"}):
            raise AssertionError

        # Test serialization
        version_dict = version.to_dict()
        restored_version = DataVersion.from_dict(version_dict)

        if not (restored_version.version_id == version.version_id):
            raise AssertionError
        if not (restored_version.file_path == version.file_path):
            raise AssertionError
        if not (restored_version.checksum == version.checksum):
            raise AssertionError
        if not (restored_version.metadata == version.metadata):
            raise AssertionError


def test_data_manager_initialization() -> None:
    """Test initializing DataManager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        dm = DataManager(data_dir, metadata_dir)

        if not (dm.data_directory == data_dir):
            raise AssertionError
        if not (dm.metadata_directory == metadata_dir):
            raise AssertionError


def test_data_manager_register_dataset() -> None:
    """Test registering a dataset."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.write_csv(test_file)

        dm = DataManager(data_dir, metadata_dir)
        version_id = dm.register_dataset(test_file, {"description": "Test data"})

        require_runtime_instance(version_id, str)
        if "test_data" not in dm.datasets:
            raise AssertionError
        if not (len(dm.datasets["test_data"]) == 1):
            raise AssertionError

        version = dm.datasets["test_data"][0]
        if not (version.version_id.startswith("test_data_")):
            raise AssertionError
        if not (version.metadata["description"] == "Test data"):
            raise AssertionError


def test_data_manager_list_datasets() -> None:
    """Test listing datasets."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create test data files
        test_file1 = data_dir / "test_data1.csv"
        test_file2 = data_dir / "test_data2.csv"
        pl.DataFrame({"a": [1, 2]}).write_csv(test_file1)
        pl.DataFrame({"b": [3, 4]}).write_csv(test_file2)

        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file1)
        dm.register_dataset(test_file2)

        datasets = dm.list_datasets()
        require_equal(len(datasets), 2)
        if "test_data1" not in datasets:
            raise AssertionError
        if "test_data2" not in datasets:
            raise AssertionError


def test_data_manager_get_dataset_info() -> None:
    """Test getting dataset info."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.write_csv(test_file)

        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)

        info = dm.get_dataset_info("test_data")
        if not (info["dataset_name"] == "test_data"):
            raise AssertionError
        if not (info["version_count"] == 1):
            raise AssertionError
        require_equal(info["row_count"], 3)
        require_equal(info["column_count"], 2)
        if "a" not in info["columns"]:
            raise AssertionError
        if "b" not in info["columns"]:
            raise AssertionError


def test_data_manager_load_dataset() -> None:
    """Test loading a dataset."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create test data file
        test_file = data_dir / "test_data.csv"
        original_data = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        original_data.write_csv(test_file)

        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)

        # Load the dataset
        loaded_data = dm.load_dataset(
            "test_data",
            schema_overrides=original_data.schema,
        )

        # Check that data is the same
        assert_frame_equal(original_data, loaded_data)


def test_data_manager_verify_integrity() -> None:
    """Test verifying dataset integrity."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create test data file
        test_file = data_dir / "test_data.csv"
        test_data = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data.write_csv(test_file)

        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file)

        # Verify integrity
        is_valid = dm.verify_integrity("test_data")
        if not (is_valid):
            raise AssertionError

        # Modify file and verify it fails
        with Path(test_file).open("a") as f:
            f.write("7,8\n")

        is_valid = dm.verify_integrity("test_data")
        if is_valid:
            raise AssertionError


def test_data_manager_multiple_versions() -> None:
    """Test handling multiple versions of a dataset."""
    expected_current_rows = 3
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data"
        metadata_dir = Path(temp_dir) / "metadata"

        data_dir.mkdir()
        metadata_dir.mkdir()

        # Create initial test data file
        test_file = data_dir / "test_data.csv"
        test_data_v1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
        test_data_v1.write_csv(test_file)

        dm = DataManager(data_dir, metadata_dir)
        dm.register_dataset(test_file, {"version": "v1"})

        # Modify data and register again
        test_data_v2 = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_data_v2.write_csv(test_file)
        version_id_2 = dm.register_dataset(test_file, {"version": "v2"})

        # Check versions
        versions = dm.get_dataset_versions("test_data")
        require_equal(len(versions), 2)

        # Check latest version
        latest = dm.get_latest_version("test_data")
        if latest is None or latest.version_id != version_id_2:
            raise AssertionError

        # Load data (will load current file content)
        data_current = dm.load_dataset("test_data")
        if not (len(data_current) == expected_current_rows):
            raise AssertionError  # Current content has 3 rows


if __name__ == "__main__":
    pytest.main([__file__])
