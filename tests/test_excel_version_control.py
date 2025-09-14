"""Tests for the Excel workbook version control system."""

import pandas as pd
import pytest
from pathlib import Path
import tempfile

from genomics_microcosting.excel_version_control import WorkbookVersionControl, WorkbookVersion


def test_workbook_version_creation():
    """Test creating a WorkbookVersion."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "test.xlsx"
        temp_path.write_text("test content")
        
        version = WorkbookVersion(
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
        restored_version = WorkbookVersion.from_dict(version_dict)
        
        assert restored_version.version_id == version.version_id
        assert restored_version.file_path == version.file_path
        assert restored_version.checksum == version.checksum
        assert restored_version.metadata == version.metadata


def test_workbook_version_control_initialization():
    """Test initializing WorkbookVersionControl."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        
        vc = WorkbookVersionControl(repo_dir)
        
        assert vc.repository_directory == repo_dir
        assert vc.workbooks_dir == repo_dir / "workbooks"
        assert vc.metadata_dir == repo_dir / "metadata"
        assert vc.workbooks_dir.exists()
        assert vc.metadata_dir.exists()


def test_workbook_version_control_commit_workbook():
    """Test committing a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df.to_excel(workbook_file, index=False)
        
        # Commit the workbook
        version_id = vc.commit_workbook(workbook_file, {"description": "Test workbook"})
        
        assert version_id is not None
        assert "test_workbook" in vc.workbooks
        assert len(vc.workbooks["test_workbook"]) == 1
        
        version = vc.workbooks["test_workbook"][0]
        assert version.version_id.startswith("test_workbook_")
        assert version.metadata["description"] == "Test workbook"
        assert version.file_path.exists()


def test_workbook_version_control_list_workbooks():
    """Test listing workbooks."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook files
        workbook_file1 = Path(temp_dir) / "workbook1.xlsx"
        workbook_file2 = Path(temp_dir) / "workbook2.xlsx"
        pd.DataFrame({"A": [1, 2]}).to_excel(workbook_file1, index=False)
        pd.DataFrame({"B": [3, 4]}).to_excel(workbook_file2, index=False)
        
        vc.commit_workbook(workbook_file1)
        vc.commit_workbook(workbook_file2)
        
        workbooks = vc.list_workbooks()
        assert len(workbooks) == 2
        assert "workbook1" in workbooks
        assert "workbook2" in workbooks


def test_workbook_version_control_get_workbook_info():
    """Test getting workbook info."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        test_data.to_excel(workbook_file, index=False)
        
        vc.commit_workbook(workbook_file)
        
        info = vc.get_workbook_info("test_workbook")
        assert info["workbook_name"] == "test_workbook"
        assert info["version_count"] == 1
        assert info["latest_version"] is not None
        assert info["file_extension"] == ".xlsx"


def test_workbook_version_control_checkout_workbook():
    """Test checking out a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        original_data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        original_data.to_excel(workbook_file, index=False)
        
        # Commit the workbook
        vc.commit_workbook(workbook_file)
        
        # Checkout the workbook
        output_file = Path(temp_dir) / "checked_out.xlsx"
        checked_out_path = vc.checkout_workbook("test_workbook", output_path=output_file)
        
        # Check that the file was created
        assert checked_out_path.exists()
        assert checked_out_path == output_file
        
        # Check that the content is the same
        checked_out_data = pd.read_excel(checked_out_path)
        pd.testing.assert_frame_equal(original_data, checked_out_data)


def test_workbook_version_control_verify_integrity():
    """Test verifying workbook integrity."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        test_data.to_excel(workbook_file, index=False)
        
        vc.commit_workbook(workbook_file)
        
        # Verify integrity
        is_valid = vc.verify_integrity("test_workbook")
        assert is_valid


def test_workbook_version_control_multiple_versions():
    """Test handling multiple versions of a workbook."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create initial test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data_v1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        test_data_v1.to_excel(workbook_file, index=False)
        
        vc.commit_workbook(workbook_file, {"version": "v1"})
        
        # Modify data and commit again
        test_data_v2 = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        test_data_v2.to_excel(workbook_file, index=False)
        version_id_2 = vc.commit_workbook(workbook_file, {"version": "v2"})
        
        # Check versions
        versions = vc.get_workbook_versions("test_workbook")
        assert len(versions) == 2
        
        # Check latest version
        latest = vc.get_latest_version("test_workbook")
        assert latest.version_id == version_id_2


def test_workbook_version_control_compare_versions():
    """Test comparing workbook versions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create initial test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data_v1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        test_data_v1.to_excel(workbook_file, index=False)
        
        version_id_1 = vc.commit_workbook(workbook_file, {"version": "v1"})
        
        # Modify data and commit again
        test_data_v2 = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        test_data_v2.to_excel(workbook_file, index=False)
        version_id_2 = vc.commit_workbook(workbook_file, {"version": "v2"})
        
        # Compare versions
        comparison = vc.compare_versions("test_workbook", version_id_1, version_id_2)
        
        assert comparison["workbook_name"] == "test_workbook"
        assert comparison["version1"] == version_id_1
        assert comparison["version2"] == version_id_2
        assert "same_checksum" in comparison


def test_workbook_version_control_same_version():
    """Test committing the same version twice."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = Path(temp_dir) / "repo"
        vc = WorkbookVersionControl(repo_dir)
        
        # Create test workbook file
        workbook_file = Path(temp_dir) / "test_workbook.xlsx"
        test_data = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        test_data.to_excel(workbook_file, index=False)
        
        # Commit the same workbook twice
        version_id_1 = vc.commit_workbook(workbook_file)
        version_id_2 = vc.commit_workbook(workbook_file)
        
        # Should return the same version ID
        assert version_id_1 == version_id_2
        
        # Should only have one version
        versions = vc.get_workbook_versions("test_workbook")
        assert len(versions) == 1


if __name__ == "__main__":
    pytest.main([__file__])