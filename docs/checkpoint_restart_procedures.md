# Checkpoint/Restart Procedures for Genomics Microcosting Analysis

## Overview

This document describes the checkpoint/restart procedures implemented in the genomics microcosting project. The system provides robust checkpoint management capabilities that allow long-running analyses to be paused and resumed, with optional persistence to disk for recovery after system restarts.

## Checkpoint Manager Architecture

The checkpoint system consists of two main components:

1. **CheckpointManager** - Core checkpoint management class with persistence capabilities
2. **ErrorHandler Integration** - Seamless integration with the error handling system

## Checkpoint Features

### In-Memory Checkpoints
- Fast creation and restoration of checkpoints
- Suitable for short-term checkpointing during analysis steps
- Automatic management within the application lifecycle

### Persistent Checkpoints
- Checkpoints saved to disk using Python's pickle serialization
- Recovery after application restarts or system failures
- Configurable checkpoint directory location

### Metadata Support
- Associate metadata with each checkpoint for better organization
- Track checkpoint creation time and context information
- Query checkpoints by metadata attributes

## Usage Examples

### Basic Checkpoint Creation and Restoration

```python
from unimelb_phd_phase_1.error_handling import setup_standard_error_handling

# Initialize error handler with checkpoint directory
error_handler = setup_standard_error_handling(
    checkpoint_dir="./analysis_checkpoints"
)

# Create checkpoint data
analysis_data = {
    "results": [1, 2, 3, 4, 5],
    "parameters": {"threshold": 0.05, "iterations": 1000},
    "metadata": {"analysis_type": "cost_driver", "version": "1.0"}
}

# Create checkpoint with metadata
checkpoint_id = error_handler.create_checkpoint(
    "cost_driver_analysis_step1",
    analysis_data,
    {"step": "initial_processing", "status": "completed"}
)

# Later, restore checkpoint
restored_data = error_handler.restore_checkpoint(checkpoint_id)
```

### Persistent Checkpoint Recovery

```python
# After application restart, create new error handler with same checkpoint directory
new_error_handler = setup_standard_error_handling(
    checkpoint_dir="./analysis_checkpoints"
)

# Restore checkpoint from disk
restored_data = new_error_handler.restore_checkpoint(
    "cost_driver_analysis_step1", 
    from_disk=True  # Load from persistent storage
)
```

### Standalone Checkpoint Manager

```python
from unimelb_phd_phase_1.error_handling import CheckpointManager

# Create standalone checkpoint manager
checkpoint_manager = CheckpointManager(
    checkpoint_dir="./my_checkpoints"
)

# Create checkpoint
checkpoint_id = checkpoint_manager.create_checkpoint(
    "my_analysis_checkpoint",
    {"key": "value"},
    {"purpose": "example"}
)

# List all checkpoints
checkpoints = checkpoint_manager.list_checkpoints()
for checkpoint in checkpoints:
    print(f"ID: {checkpoint['id']}")
    print(f"Created: {checkpoint['datetime']}")
    print(f"Metadata: {checkpoint['metadata']}")

# Delete checkpoint when no longer needed
checkpoint_manager.delete_checkpoint(checkpoint_id)
```

## Checkpoint Data Structure

Each checkpoint contains the following information:

- **id**: Unique identifier for the checkpoint
- **data**: The actual data being checkpointed
- **metadata**: Additional information about the checkpoint
- **timestamp**: Unix timestamp of checkpoint creation
- **datetime**: ISO format datetime string of checkpoint creation

## Best Practices

### Checkpoint Naming
- Use descriptive checkpoint IDs that indicate the analysis step
- Include version information when relevant
- Follow a consistent naming convention across the project

### Checkpoint Frequency
- Create checkpoints at major analysis milestones
- Avoid excessive checkpointing which can impact performance
- Consider the size of data being checkpointed

### Metadata Usage
- Include sufficient metadata to identify checkpoint purpose
- Track analysis parameters and context information
- Use metadata for checkpoint organization and querying

### Storage Management
- Regularly clean up old checkpoints that are no longer needed
- Monitor disk space usage for persistent checkpoints
- Consider archiving important checkpoints for long-term storage

## Integration with Error Handling

The checkpoint system is fully integrated with the error handling framework:

```python
# Create checkpoint during error handling
try:
    result = complex_analysis_function()
except Exception as e:
    # Save error context as checkpoint
    error_context = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "partial_results": partial_analysis_data
    }
    
    checkpoint_id = error_handler.create_checkpoint(
        "analysis_error_recovery",
        error_context,
        {"error_handling": True, "recovery_point": True}
    )
    
    # Attempt recovery using checkpoint
    # ... recovery logic ...
```

## Performance Considerations

### Memory Usage
- In-memory checkpoints are fast but consume RAM
- Large datasets should use persistent checkpoints when possible
- Monitor memory usage during intensive checkpointing operations

### Disk I/O
- Persistent checkpoints involve disk I/O operations
- Consider using SSD storage for checkpoint directories
- Batch checkpoint operations when possible to reduce I/O overhead

### Serialization Overhead
- Python's pickle is used for serialization
- Very large objects may have significant serialization overhead
- Consider checkpointing smaller, more focused data structures

## Security Considerations

### Data Protection
- Checkpoint files contain serialized Python objects
- Store checkpoint directories with appropriate file permissions
- Consider encryption for sensitive analysis data

### Directory Management
- Validate checkpoint directory paths to prevent directory traversal
- Use dedicated directories for checkpoint storage
- Regularly audit checkpoint directory contents

## Troubleshooting

### Common Issues

1. **Checkpoint Not Found**
   - Verify checkpoint ID spelling
   - Check if checkpoint was created with persistence
   - Confirm checkpoint directory path is correct

2. **Permission Errors**
   - Ensure write permissions on checkpoint directory
   - Check file ownership and permissions
   - Verify sufficient disk space is available

3. **Serialization Errors**
   - Some Python objects cannot be pickled
   - Use serializable data structures in checkpoints
   - Consider alternative serialization methods for complex objects

### Diagnostic Information
- Check application logs for checkpoint-related messages
- Verify checkpoint files exist in the checkpoint directory
- Use `list_checkpoints()` to verify available checkpoints