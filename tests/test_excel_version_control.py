# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for the Excel workbook version control system."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from openpyxl import Workbook
from polars.testing import assert_frame_equal

from genomics_microcosting.excel_version_control import (
    WorkbookVersion,
    WorkbookVersionControl,
)
from tests.checks import require_equal, require_runtime_instance


def test_workbook_version_creation() -> None:
    """Test creating a WorkbookVersion."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "test.xlsx"
        temp_path.write_text("test content")

        version = WorkbookVersion(
            version_id="test_v1",
            timestamp=datetime.now(UTC),
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
        restored_version = WorkbookVersion.from_dict(version_dict)

        if not (restored_version.version_id == version.version_id):
            raise AssertionError
        if not (restored_version.file_path == version.file_path):
            raise AssertionError
        if not (restored_version.checksum == version.checksum):
            raise AssertionError
        if not (restored_version.metadata == version.metadata):
            raise AssertionError


def test_workbook_version_control_initialization() -> None:
    """Test initializing WorkbookVersionControl."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"

        vc = WorkbookVersionControl(repo_dir)

        if not (vc.repository_directory == repo_dir):
            raise AssertionError
        if not (vc.workbooks_dir == repo_dir / "workbooks"):
            raise AssertionError
        if not (vc.metadata_dir == repo_dir / "metadata"):
            raise AssertionError
        if not (vc.workbooks_dir.exists()):
            raise AssertionError
        if not (vc.metadata_dir.exists()):
            raise AssertionError


def test_workbook_version_control_commit_workbook() -> None:
    """Test committing a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(df, workbook_file)

        # Commit the workbook
        version_id = vc.commit_workbook(workbook_file, {"description": "Test workbook"})

        require_runtime_instance(version_id, str)
        if "test_workbook" not in vc.workbooks:
            raise AssertionError
        if not (len(vc.workbooks["test_workbook"]) == 1):
            raise AssertionError

        version = vc.workbooks["test_workbook"][0]
        if not (version.version_id.startswith("test_workbook_")):
            raise AssertionError
        if not (version.metadata["description"] == "Test workbook"):
            raise AssertionError
        if not (version.file_path.exists()):
            raise AssertionError


def test_workbook_version_control_list_workbooks() -> None:
    """Test listing workbooks."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook files
        workbook_file1 = Path(temp_dir) / "workbook1.xlsx"
        workbook_file2 = Path(temp_dir) / "workbook2.xlsx"
        _write_workbook(pl.DataFrame({"A": [1, 2]}), workbook_file1)
        _write_workbook(pl.DataFrame({"B": [3, 4]}), workbook_file2)

        vc.commit_workbook(workbook_file1)
        vc.commit_workbook(workbook_file2)

        workbooks = vc.list_workbooks()
        require_equal(len(workbooks), 2)
        if "workbook1" not in workbooks:
            raise AssertionError
        if "workbook2" not in workbooks:
            raise AssertionError


def test_workbook_version_control_get_workbook_info() -> None:
    """Test getting workbook info."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(test_data, workbook_file)

        vc.commit_workbook(workbook_file)

        info = vc.get_workbook_info("test_workbook")
        if not (info["workbook_name"] == "test_workbook"):
            raise AssertionError
        if not (info["version_count"] == 1):
            raise AssertionError
        if not (info["latest_version"] is not None):
            raise AssertionError
        if not (info["file_extension"] == ".xlsx"):
            raise AssertionError


def test_workbook_version_control_checkout_workbook() -> None:
    """Test checking out a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        original_data = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(original_data, workbook_file)

        # Commit the workbook
        vc.commit_workbook(workbook_file)

        # Checkout the workbook
        output_file = Path(temp_dir) / "checked_out.xlsx"
        checked_out_path = vc.checkout_workbook(
            "test_workbook",
            output_path=output_file,
        )

        # Check that the file was created
        if not (checked_out_path.exists()):
            raise AssertionError
        if not (checked_out_path == output_file):
            raise AssertionError

        # Check that the content is the same
        checked_out_data = pl.read_excel(checked_out_path, engine="openpyxl")
        assert_frame_equal(original_data, checked_out_data)


def test_workbook_version_control_verify_integrity() -> None:
    """Test verifying workbook integrity."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(test_data, workbook_file)

        vc.commit_workbook(workbook_file)

        # Verify integrity
        is_valid = vc.verify_integrity("test_workbook")
        if not (is_valid):
            raise AssertionError


def test_workbook_version_control_multiple_versions() -> None:
    """Test handling multiple versions of a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create initial test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data_v1 = pl.DataFrame({"A": [1, 2], "B": [3, 4]})
        _write_workbook(test_data_v1, workbook_file)

        vc.commit_workbook(workbook_file, {"version": "v1"})

        # Modify data and commit again
        test_data_v2 = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(test_data_v2, workbook_file)
        version_id_2 = vc.commit_workbook(workbook_file, {"version": "v2"})

        # Check versions
        versions = vc.get_workbook_versions("test_workbook")
        require_equal(len(versions), 2)

        # Check latest version
        latest = vc.get_latest_version("test_workbook")
        if latest is None or latest.version_id != version_id_2:
            raise AssertionError


def test_workbook_version_control_compare_versions() -> None:
    """Test comparing workbook versions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create initial test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data_v1 = pl.DataFrame({"A": [1, 2], "B": [3, 4]})
        _write_workbook(test_data_v1, workbook_file)

        version_id_1 = vc.commit_workbook(workbook_file, {"version": "v1"})

        # Modify data and commit again
        test_data_v2 = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(test_data_v2, workbook_file)
        version_id_2 = vc.commit_workbook(workbook_file, {"version": "v2"})

        # Compare versions
        comparison = vc.compare_versions("test_workbook", version_id_1, version_id_2)

        if not (comparison["workbook_name"] == "test_workbook"):
            raise AssertionError
        if not (comparison["version1"] == version_id_1):
            raise AssertionError
        if not (comparison["version2"] == version_id_2):
            raise AssertionError
        if "same_checksum" not in comparison:
            raise AssertionError


def test_workbook_version_control_same_version() -> None:
    """Test committing the same version twice."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)

        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        _write_workbook(test_data, workbook_file)

        # Commit the same workbook twice
        version_id_1 = vc.commit_workbook(workbook_file)
        version_id_2 = vc.commit_workbook(workbook_file)

        # Should return the same version ID
        if not (version_id_1 == version_id_2):
            raise AssertionError

        # Should only have one version
        versions = vc.get_workbook_versions("test_workbook")
        if not (len(versions) == 1):
            raise AssertionError


def _write_workbook(frame: pl.DataFrame, path: Path) -> None:
    """Write synthetic workbook fixtures through the existing openpyxl dependency."""
    workbook = Workbook()
    worksheet = workbook.active
    if worksheet is None:
        raise AssertionError
    worksheet.title = "Sheet1"
    worksheet.append(frame.columns)
    for row in frame.iter_rows():
        worksheet.append(row)
    workbook.save(path)
    workbook.close()


if __name__ == "__main__":
    pytest.main([__file__])
