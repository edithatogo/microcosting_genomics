# Configuration Management Procedures

## Overview

This document outlines the procedures for implementing and using the enhanced Configuration Management system in the Genomics Microcosting Project. The system provides comprehensive configuration management capabilities including parameter validation, environment-specific configurations, configuration versioning, and dynamic configuration updates.

## System Components

### 1. ConfigurationValidator Class

Validates configuration parameters and structures to ensure they meet defined constraints.

#### Key Methods:
- `validate_parameter()`: Validates a single parameter against its constraints
- `validate_analysis_config()`: Validates an entire analysis configuration

### 2. EnvironmentConfigurationManager Class

Manages environment-specific configurations, allowing different settings for development, testing, and production environments.

#### Key Methods:
- `add_environment()`: Adds or updates an environment configuration
- `get_environment_config()`: Gets configuration for a specific environment

### 3. ConfigurationVersionManager Class

Manages configuration versioning for reproducible research, allowing researchers to track and retrieve specific versions of configurations.

#### Key Methods:
- `create_version()`: Creates a version of a configuration
- `get_version()`: Retrieves a specific version of a configuration
- `list_versions()`: Lists all versions of a configuration

### 4. DynamicConfigurationUpdater Class

Handles dynamic configuration updates during runtime, allowing parameters to be modified without restarting the application.

#### Key Methods:
- `update_parameter()`: Dynamically updates a configuration parameter
- `register_update_listener()`: Registers callbacks for configuration updates

## Implementation Procedures

### 1. Configuration Parameter Validation

The system validates configuration parameters to ensure they meet defined constraints such as data types, value ranges, and allowed choices.

#### Implementation Example:
```python
from unimelb_phd_phase_1.config_validation import ConfigurationValidator
from unimelb_phd_phase_1.analysis_config import AnalysisParameter

# Create validator
validator = ConfigurationValidator()

# Create a parameter with constraints
parameter = AnalysisParameter(
    name="monte_carlo_iterations",
    value=1000,
    description="Number of Monte Carlo iterations",
    data_type="int",
    default_value=1000,
    min_value=100,
    max_value=100000,
)

# Validate the parameter
validation_result = validator.validate_parameter(parameter)
if validation_result["passed"]:
    print("Parameter is valid")
else:
    print(f"Parameter validation failed: {validation_result['errors']}")
```

### 2. Environment-Specific Configurations

The system supports different configurations for different environments (development, testing, production) by applying overrides to base configurations.

#### Implementation Example:
```python
from unimelb_phd_phase_1.config_validation import EnvironmentConfigurationManager
from unimelb_phd_phase_1.analysis_config import AnalysisConfigurationManager

# Create configuration managers
base_config_manager = AnalysisConfigurationManager()
env_manager = EnvironmentConfigurationManager(base_config_manager)

# Add development environment overrides
dev_overrides = {
    "parameters": {
        "top_n_drivers": 5,  # Smaller number for faster development testing
        "monte_carlo_iterations": 100,  # Fewer iterations for development
    }
}
env_manager.add_environment("development", dev_overrides)

# Get environment-specific configuration
dev_config = env_manager.get_environment_config("development", "cost_driver_analysis")
print(
    f"Development config top_n_drivers: {dev_config.parameters['top_n_drivers'].value}"
)
```

### 3. Configuration Versioning

The system provides configuration versioning for reproducible research, allowing researchers to track and retrieve specific versions of configurations.

#### Implementation Example:
```python
from unimelb_phd_phase_1.config_validation import ConfigurationVersionManager
from unimelb_phd_phase_1.analysis_config import AnalysisConfigurationManager
from pathlib import Path

# Create version manager
config_dir = Path("configs")
version_manager = ConfigurationVersionManager(config_dir)

# Get a configuration to version
config_manager = AnalysisConfigurationManager()
config = config_manager.get_configuration("psa_analysis")

# Create a version
version_hash = version_manager.create_version(
    config, "Initial version for paper submission"
)
print(f"Created version: {version_hash}")

# List versions
versions = version_manager.list_versions("psa_analysis")
for version in versions:
    print(f"Version {version['hash']} created at {version['created_at']}")

# Retrieve a specific version
retrieved_config = version_manager.get_version("psa_analysis", version_hash)
if retrieved_config:
    print(f"Retrieved configuration version: {retrieved_config.version}")
```

### 4. Dynamic Configuration Updates

The system supports dynamic configuration updates during runtime, allowing parameters to be modified without restarting the application.

#### Implementation Example:
```python
from unimelb_phd_phase_1.config_validation import (
    DynamicConfigurationUpdater,
    setup_standard_config_validation,
)
from unimelb_phd_phase_1.analysis_config import AnalysisConfigurationManager

# Create configuration managers
config_manager = AnalysisConfigurationManager()
validator = setup_standard_config_validation()
updater = DynamicConfigurationUpdater(config_manager, validator)


# Define an update listener
def on_config_update(config_name, parameter_name, new_value):
    print(f"Configuration updated: {config_name}.{parameter_name} = {new_value}")


# Register the listener
updater.register_update_listener(on_config_update)

# Dynamically update a parameter
success = updater.update_parameter("cost_driver_analysis", "top_n_drivers", 15)
if success:
    print("Parameter updated successfully")
else:
    print("Parameter update failed")
```

## Best Practices

### 1. Configuration Validation
- Always validate configurations before using them in analysis
- Define appropriate constraints for parameters (data types, ranges, choices)
- Provide meaningful error messages for validation failures

### 2. Environment Management
- Use environment-specific configurations to optimize for each environment
- Keep sensitive configuration values (like credentials) in secure environment variables
- Document environment differences clearly

### 3. Version Control
- Create configuration versions for significant changes
- Include descriptive notes when creating versions
- Use versioning to ensure reproducible research results

### 4. Dynamic Updates
- Register update listeners to respond to configuration changes
- Validate parameter values before applying dynamic updates
- Log configuration changes for audit purposes

## Integration with Other Systems

### Error Handling Integration
The configuration validation system integrates with the error handling framework to provide graceful degradation when configuration issues are detected.

### Logging Integration
All configuration management activities are logged through the standard logging system for audit and debugging purposes.

### Data Quality Integration
Configuration validation ensures that analysis parameters meet quality standards before processing begins.

## Testing Procedures

### Unit Testing
Each component has comprehensive unit tests that verify functionality:

1. **ConfigurationValidator Tests**: Verify parameter and configuration validation
2. **EnvironmentConfigurationManager Tests**: Confirm environment-specific configuration management
3. **ConfigurationVersionManager Tests**: Validate version creation, retrieval, and listing
4. **DynamicConfigurationUpdater Tests**: Test dynamic parameter updates and listener notifications

### Integration Testing
Integration tests verify that the configuration management system works correctly with the analysis configuration system.

## Troubleshooting

### Common Issues

1. **Validation Failures**: Check that parameter values meet defined constraints
2. **Environment Configuration Not Found**: Verify environment name spelling and registration
3. **Version Retrieval Failures**: Confirm version hash and configuration name are correct
4. **Dynamic Update Failures**: Ensure parameter names and values are valid

### Diagnostic Procedures

1. **Check Logs**: Review detailed logs for specific error messages
2. **Validate Configuration**: Use the validator to check configuration validity
3. **Verify Environment Setup**: Confirm environment configurations are properly registered
4. **Test Components Individually**: Isolate issues by testing individual components

## Future Enhancements

### Planned Improvements
1. **Configuration Templates**: Pre-defined configuration templates for common analysis scenarios
2. **Remote Configuration Management**: Support for centralized configuration management
3. **Configuration Diff Tool**: Visual comparison of configuration versions
4. **Automated Configuration Testing**: Automated testing of configuration combinations

### Extensibility Points
1. **Custom Validators**: Allow for domain-specific parameter validation
2. **Pluggable Environment Providers**: Support for different environment configuration sources
3. **Extended Versioning Features**: Enhanced versioning with branching and merging
4. **Advanced Update Strategies**: Sophisticated dynamic update mechanisms