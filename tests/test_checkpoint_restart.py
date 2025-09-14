"""Test checkpoint/restart capabilities for genomics microcosting analysis.

This module tests the enhanced checkpoint/restart capabilities with persistence.
"""

import unittest
import sys
import logging
import tempfile
import shutil
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.error_handling import (  # noqa: E402
    CheckpointManager,
    setup_standard_error_handling
)


class TestCheckpointRestart(unittest.TestCase):
    """Test checkpoint/restart capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a logger for testing
        self.logger = logging.getLogger('test_checkpoint')
        self.logger.setLevel(logging.DEBUG)
        
        # Create temporary directory for checkpoints
        self.temp_checkpoint_dir = tempfile.mkdtemp()
        
        # Create error handler with checkpoint directory
        self.error_handler = setup_standard_error_handling(
            logger=self.logger, 
            checkpoint_dir=self.temp_checkpoint_dir
        )
        
        # Create standalone checkpoint manager for testing
        self.checkpoint_manager = CheckpointManager(
            logger=self.logger, 
            checkpoint_dir=self.temp_checkpoint_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary checkpoint directory
        try:
            shutil.rmtree(self.temp_checkpoint_dir)
        except (OSError, FileNotFoundError):
            pass
    
    def test_create_and_restore_checkpoint(self):
        """Test creating and restoring checkpoints."""
        # Test data
        test_data = {
            "analysis_results": [1, 2, 3, 4, 5],
            "metadata": {"version": "1.0", "timestamp": "2023-01-01"},
            "parameters": {"threshold": 0.05, "iterations": 1000}
        }
        
        # Create checkpoint
        checkpoint_id = self.error_handler.create_checkpoint(
            "test_checkpoint", 
            test_data,
            {"purpose": "testing", "status": "complete"}
        )
        
        # Verify checkpoint was created
        self.assertIsNotNone(checkpoint_id)
        self.assertIsInstance(checkpoint_id, str)
        
        # Restore checkpoint
        restored_data = self.error_handler.restore_checkpoint(checkpoint_id)
        
        # Verify restored data matches original
        self.assertEqual(restored_data, test_data)
    
    def test_persistent_checkpoint_storage(self):
        """Test that checkpoints are stored persistently."""
        # Test data
        test_data = {"key": "value", "numbers": [1, 2, 3]}
        
        # Create checkpoint
        checkpoint_id = self.error_handler.create_checkpoint(
            "persistent_test", 
            test_data
        )
        
        # Verify checkpoint file exists
        checkpoint_file = Path(self.temp_checkpoint_dir) / f"{checkpoint_id}.pkl"
        self.assertTrue(checkpoint_file.exists())
        
        # Create new error handler to simulate restart
        new_error_handler = setup_standard_error_handling(
            logger=self.logger, 
            checkpoint_dir=self.temp_checkpoint_dir
        )
        
        # Restore checkpoint from disk
        restored_data = new_error_handler.restore_checkpoint(checkpoint_id, from_disk=True)
        
        # Verify restored data matches original
        self.assertEqual(restored_data, test_data)
    
    def test_checkpoint_manager_standalone(self):
        """Test CheckpointManager functionality independently."""
        # Test data
        test_data = {"standalone": True, "values": [10, 20, 30]}
        
        # Create checkpoint
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            "standalone_test", 
            test_data,
            {"type": "standalone", "test": True}
        )
        
        # Verify checkpoint was created
        self.assertIsNotNone(checkpoint_id)
        
        # List checkpoints
        checkpoints = self.checkpoint_manager.list_checkpoints()
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(checkpoints[0]['id'], checkpoint_id)
        self.assertIn('type', checkpoints[0]['metadata'])
        self.assertEqual(checkpoints[0]['metadata']['type'], 'standalone')
        
        # Restore checkpoint
        restored_data = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        self.assertEqual(restored_data, test_data)
        
        # Delete checkpoint
        self.checkpoint_manager.delete_checkpoint(checkpoint_id)
        
        # Verify checkpoint is deleted
        checkpoints_after = self.checkpoint_manager.list_checkpoints()
        self.assertEqual(len(checkpoints_after), 0)
        
        # Verify file is deleted
        checkpoint_file = Path(self.temp_checkpoint_dir) / f"{checkpoint_id}.pkl"
        self.assertFalse(checkpoint_file.exists())
    
    def test_checkpoint_with_no_id(self):
        """Test creating checkpoint with auto-generated ID."""
        test_data = {"auto_id": True}
        
        # Create checkpoint without specifying ID
        checkpoint_id = self.checkpoint_manager.create_checkpoint(
            None,  # No ID specified
            test_data
        )
        
        # Verify ID was generated
        self.assertIsNotNone(checkpoint_id)
        self.assertIsInstance(checkpoint_id, str)
        self.assertTrue(checkpoint_id.startswith("checkpoint_"))
        
        # Restore checkpoint
        restored_data = self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        self.assertEqual(restored_data, test_data)
    
    def test_restore_nonexistent_checkpoint(self):
        """Test restoring a nonexistent checkpoint."""
        # Try to restore checkpoint that doesn't exist
        restored_data = self.error_handler.restore_checkpoint("nonexistent_checkpoint")
        
        # Should return None
        self.assertIsNone(restored_data)
    
    def test_list_checkpoints(self):
        """Test listing available checkpoints."""
        # Create multiple checkpoints
        data1 = {"test": 1}
        data2 = {"test": 2}
        
        id1 = self.checkpoint_manager.create_checkpoint("checkpoint_1", data1, {"order": 1})
        id2 = self.checkpoint_manager.create_checkpoint("checkpoint_2", data2, {"order": 2})
        
        # List checkpoints
        checkpoints = self.checkpoint_manager.list_checkpoints()
        
        # Verify we have 2 checkpoints
        self.assertEqual(len(checkpoints), 2)
        
        # Verify checkpoint information
        checkpoint_ids = [cp['id'] for cp in checkpoints]
        self.assertIn(id1, checkpoint_ids)
        self.assertIn(id2, checkpoint_ids)
        
        # Verify metadata
        for checkpoint in checkpoints:
            self.assertIn('timestamp', checkpoint)
            self.assertIn('datetime', checkpoint)
            self.assertIn('metadata', checkpoint)
    
    def test_checkpoint_integration_with_error_handling(self):
        """Test checkpoint integration with error handling."""
        # Create checkpoint during error handling
        try:
            raise ValueError("Test error for checkpoint integration")
        except Exception as e:
            # Create checkpoint with error context
            error_context_data = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "handled_at": "test_integration"
            }
            
            checkpoint_id = self.error_handler.create_checkpoint(
                "error_context_checkpoint",
                error_context_data,
                {"error_handling": True, "test": True}
            )
            
            # Verify checkpoint was created
            self.assertIsNotNone(checkpoint_id)
            
            # Restore checkpoint
            restored_data = self.error_handler.restore_checkpoint(checkpoint_id)
            self.assertEqual(restored_data, error_context_data)


if __name__ == '__main__':
    unittest.main()