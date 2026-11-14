# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test checkpoint/restart capabilities for genomics microcosting analysis.

This module tests the enhanced checkpoint/restart capabilities with persistence.
"""

import contextlib
import logging
import shutil
import tempfile
import unittest
from pathlib import Path

from genomics_microcosting.error_handling import (
    CheckpointManager,
    setup_standard_error_handling,
)
from tests.checks import require_equal, require_runtime_instance


def _raise_test_error(error: Exception) -> None:
    raise error


class TestCheckpointRestart(unittest.TestCase):
    """Test checkpoint/restart capabilities."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger("test_checkpoint")
        self.logger.setLevel(logging.DEBUG)

        # Create temporary directory for checkpoints
        self.temp_checkpoint_dir = tempfile.mkdtemp()

        # Create error handler with checkpoint directory
        self.error_handler = setup_standard_error_handling(
            logger=self.logger,
            checkpoint_dir=self.temp_checkpoint_dir,
        )

        # Create standalone checkpoint manager for testing
        self.checkpoint_manager = CheckpointManager(
            logger=self.logger,
            checkpoint_dir=self.temp_checkpoint_dir,
        )

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Remove temporary checkpoint directory
        with contextlib.suppress(OSError, FileNotFoundError):
            shutil.rmtree(self.temp_checkpoint_dir)

    def test_create_and_restore_checkpoint(self) -> None:
        """Test creating and restoring checkpoints."""
        # Test data
        test_data = {
            "analysis_results": [1, 2, 3, 4, 5],
            "metadata": {"version": "1.0", "timestamp": "2023-01-01"},
            "parameters": {"threshold": 0.05, "iterations": 1000},
        }

        # Create checkpoint
        checkpoint_id = self.error_handler.create_checkpoint(
            "test_checkpoint",
            test_data,
            {"purpose": "testing", "status": "complete"},
        )

        # Verify checkpoint was created
        require_runtime_instance(checkpoint_id, str)

        # Restore checkpoint
        restored_data = self.error_handler.restore_checkpoint(checkpoint_id)

        # Verify restored data matches original
        if not ((restored_data) == (test_data)):
            raise AssertionError

    def test_persistent_checkpoint_storage(self) -> None:
        """Test that checkpoints are stored persistently."""
        # Test data
        test_data = {"key": "value", "numbers": [1, 2, 3]}

        # Create checkpoint
        checkpoint_id = self.error_handler.create_checkpoint(
            "persistent_test",
            test_data,
        )

        # Verify checkpoint file exists
        checkpoint_file = Path(self.temp_checkpoint_dir) / f"{checkpoint_id}.json"
        if not (checkpoint_file.exists()):
            raise AssertionError

        # Create new error handler to simulate restart
        new_error_handler = setup_standard_error_handling(
            logger=self.logger,
            checkpoint_dir=self.temp_checkpoint_dir,
        )

        # Restore checkpoint from disk
        restored_data = new_error_handler.restore_checkpoint(
            checkpoint_id,
            from_disk=True,
        )

        # Verify restored data matches original
        if not ((restored_data) == (test_data)):
            raise AssertionError

    def test_checkpoint_manager_standalone(self) -> None:
        """Test CheckpointManager functionality independently."""
        # Test data
        test_data = {"standalone": True, "values": [10, 20, 30]}

        # Create checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            "standalone_test",
            test_data,
            {"type": "standalone", "test": True},
        )

        # Verify checkpoint was created
        require_runtime_instance(checkpoint_id, str)

        # List checkpoints
        checkpoints = self.checkpoint_manager.list_checkpoints()
        if not ((len(checkpoints)) == (1)):
            raise AssertionError
        if not ((checkpoints[0]["id"]) == (checkpoint_id)):
            raise AssertionError
        if ("type") not in (checkpoints[0]["metadata"]):
            raise AssertionError
        if not ((checkpoints[0]["metadata"]["type"]) == ("standalone")):
            raise AssertionError

        # Restore checkpoint
        restored_data = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        if not ((restored_data) == (test_data)):
            raise AssertionError

        # Delete checkpoint
        self.checkpoint_manager.delete_checkpoint(checkpoint_id)

        # Verify checkpoint is deleted
        checkpoints_after = self.checkpoint_manager.list_checkpoints()
        if not ((len(checkpoints_after)) == (0)):
            raise AssertionError

        # Verify file is deleted
        checkpoint_file = Path(self.temp_checkpoint_dir) / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            raise AssertionError

    def test_checkpoint_with_no_id(self) -> None:
        """Test creating checkpoint with auto-generated ID."""
        test_data = {"auto_id": True}

        # Create checkpoint without specifying ID
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            None,  # No ID specified
            test_data,
        )

        # Verify ID was generated
        require_runtime_instance(checkpoint_id, str)
        if not (checkpoint_id.startswith("checkpoint_")):
            raise AssertionError

        # Restore checkpoint
        restored_data = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        if not ((restored_data) == (test_data)):
            raise AssertionError

    def test_restore_nonexistent_checkpoint(self) -> None:
        """Test restoring a nonexistent checkpoint."""
        # Try to restore checkpoint that doesn't exist
        restored_data = self.error_handler.restore_checkpoint("nonexistent_checkpoint")

        # Should return None
        if (restored_data) is not None:
            raise AssertionError

    def test_list_checkpoints(self) -> None:
        """Test listing available checkpoints."""
        # Create multiple checkpoints
        data1 = {"test": 1}
        data2 = {"test": 2}

        id1 = self.checkpoint_manager.create_checkpoint(
            "checkpoint_1",
            data1,
            {"order": 1},
        )
        id2 = self.checkpoint_manager.create_checkpoint(
            "checkpoint_2",
            data2,
            {"order": 2},
        )

        # List checkpoints
        checkpoints = self.checkpoint_manager.list_checkpoints()

        # Verify we have 2 checkpoints
        require_equal(len(checkpoints), 2)

        # Verify checkpoint information
        checkpoint_ids = [cp["id"] for cp in checkpoints]
        if (id1) not in (checkpoint_ids):
            raise AssertionError
        if (id2) not in (checkpoint_ids):
            raise AssertionError

        # Verify metadata
        for checkpoint in checkpoints:
            if ("timestamp") not in (checkpoint):
                raise AssertionError
            if ("datetime") not in (checkpoint):
                raise AssertionError
            if ("metadata") not in (checkpoint):
                raise AssertionError

    def test_checkpoint_integration_with_error_handling(self) -> None:
        """Test checkpoint integration with error handling."""
        # Create checkpoint during error handling
        try:
            message = "Test error for checkpoint integration"
            _raise_test_error(ValueError(message))
        except Exception as e:
            # Create checkpoint with error context
            error_context_data = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "handled_at": "test_integration",
            }

            checkpoint_id = self.error_handler.create_checkpoint(
                "error_context_checkpoint",
                error_context_data,
                {"error_handling": True, "test": True},
            )

            # Verify checkpoint was created
            require_runtime_instance(checkpoint_id, str)

            # Restore checkpoint
            restored_data = self.error_handler.restore_checkpoint(checkpoint_id)
            if not ((restored_data) == (error_context_data)):
                raise AssertionError from e


if __name__ == "__main__":
    unittest.main()
