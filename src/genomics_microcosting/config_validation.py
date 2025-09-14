"""Configuration validation for genomics microcosting analysis.

This module provides comprehensive configuration validation capabilities including
parameter validation, environment-specific configurations, configuration versioning,
and dynamic configuration updates.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
import hashlib

from .logging_config import get_logger
from .analysis_config import AnalysisConfigurationManager, AnalysisConfig, AnalysisParameter
from .input_validation import InputValidator, ValidationError


logger = get_logger(__name__)


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    pass


class ConfigurationValidator:
    """Validates configuration parameters and structures."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the configuration validator.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)
        self.analysis_config_manager = AnalysisConfigurationManager()
    
    def validate_parameter(self, parameter: AnalysisParameter) -> Dict[str, Any]:
        """Validate a single parameter.
        
        Args:
            parameter: AnalysisParameter to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "parameter": parameter.name,
            "passed": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Validate data type
            if not self._validate_data_type(parameter):
                results["passed"] = False
                results["errors"].append(f"Invalid data type: {parameter.data_type}")
            
            # Validate value against constraints
            if not self._validate_constraints(parameter):
                results["passed"] = False
                results["errors"].append("Value does not meet constraints")
                
            # Validate choices if specified
            if parameter.choices and parameter.value not in parameter.choices:
                results["passed"] = False
                results["errors"].append(f"Value {parameter.value} not in allowed choices: {parameter.choices}")
                
        except Exception as e:
            results["passed"] = False
            results["errors"].append(f"Error during parameter validation: {e}")
            
        return results
    
    def _validate_data_type(self, parameter: AnalysisParameter) -> bool:
        """Validate that parameter value matches declared data type.
        
        Args:
            parameter: AnalysisParameter to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if parameter.data_type == "int":
                self.validator.validate_numeric_value(parameter.value, allow_none=not parameter.required)
                if parameter.value is not None and not isinstance(parameter.value, int):
                    # Try to convert to int
                    int(parameter.value)
            elif parameter.data_type == "float":
                self.validator.validate_numeric_value(parameter.value, allow_none=not parameter.required)
            elif parameter.data_type == "str":
                self.validator.validate_string_value(parameter.value, allow_empty=True)
            elif parameter.data_type == "bool":
                if parameter.value is not None and not isinstance(parameter.value, bool):
                    # Try to convert to bool
                    if isinstance(parameter.value, str):
                        if parameter.value.lower() not in ['true', 'false', '1', '0']:
                            return False
                    else:
                        bool(parameter.value)
            elif parameter.data_type == "list":
                if parameter.value is not None and not isinstance(parameter.value, list):
                    return False
            elif parameter.data_type == "dict":
                if parameter.value is not None and not isinstance(parameter.value, dict):
                    return False
            else:
                # Unknown data type
                return False
                
            return True
        except (ValidationError, ValueError, TypeError):
            return False
    
    def _validate_constraints(self, parameter: AnalysisParameter) -> bool:
        """Validate parameter value against constraints.
        
        Args:
            parameter: AnalysisParameter to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate min/max for numeric types
            if parameter.data_type in ["int", "float"] and parameter.value is not None:
                if parameter.min_value is not None:
                    self.validator.validate_numeric_value(parameter.value, min_value=parameter.min_value)
                if parameter.max_value is not None:
                    self.validator.validate_numeric_value(parameter.value, max_value=parameter.max_value)
                    
            # Validate required parameters
            if parameter.required and parameter.value is None:
                raise ValidationError("Required parameter cannot be None")
                
            return True
        except ValidationError:
            return False
    
    def validate_analysis_config(self, config: AnalysisConfig) -> Dict[str, Any]:
        """Validate an entire analysis configuration.
        
        Args:
            config: AnalysisConfig to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "config": config.analysis_type,
            "passed": True,
            "errors": [],
            "warnings": [],
            "parameter_results": []
        }
        
        try:
            # Validate each parameter
            for param_name, parameter in config.parameters.items():
                param_result = self.validate_parameter(parameter)
                results["parameter_results"].append(param_result)
                
                if not param_result["passed"]:
                    results["passed"] = False
                    results["errors"].extend([f"{param_name}: {error}" for error in param_result["errors"]])
                    
            # Validate required fields
            if not config.analysis_type:
                results["passed"] = False
                results["errors"].append("Analysis type is required")
                
            if not config.version:
                results["passed"] = False
                results["errors"].append("Version is required")
                
            if not config.description:
                results["warnings"].append("Description is recommended")
                
        except Exception as e:
            results["passed"] = False
            results["errors"].append(f"Error during configuration validation: {e}")
            
        return results


class EnvironmentConfigurationManager:
    """Manages environment-specific configurations."""
    
    def __init__(self, base_config_manager: AnalysisConfigurationManager, 
                 logger: logging.Logger = None):
        """Initialize the environment configuration manager.
        
        Args:
            base_config_manager: Base analysis configuration manager
            logger: Logger instance (optional)
        """
        self.base_config_manager = base_config_manager
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.environments = {}  # environment_name -> config_overrides
        
    def add_environment(self, environment_name: str, config_overrides: Dict[str, Any]) -> bool:
        """Add or update an environment configuration.
        
        Args:
            environment_name: Name of the environment (e.g., 'development', 'testing', 'production')
            config_overrides: Configuration overrides for this environment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.validator = InputValidator(self.logger)
            self.validator.validate_string_value(environment_name, max_length=50)
            
            # Store the environment configuration
            self.environments[environment_name] = config_overrides
            self.logger.info(f"Added environment configuration: {environment_name}")
            return True
        except ValidationError as e:
            self.logger.error(f"Invalid environment name: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error adding environment {environment_name}: {e}")
            return False
    
    def get_environment_config(self, environment_name: str, 
                             base_config_name: str) -> Optional[AnalysisConfig]:
        """Get configuration for a specific environment.
        
        Args:
            environment_name: Name of the environment
            base_config_name: Name of the base configuration to override
            
        Returns:
            AnalysisConfig with environment overrides applied, or None if not found
        """
        try:
            # Get the base configuration
            base_config = self.base_config_manager.get_configuration(base_config_name)
            if base_config is None:
                self.logger.warning(f"Base configuration {base_config_name} not found")
                return None
                
            # Check if environment exists
            if environment_name not in self.environments:
                self.logger.warning(f"Environment {environment_name} not found")
                return base_config  # Return base config if no environment overrides
                
            # Apply environment overrides
            env_overrides = self.environments[environment_name]
            env_config = self._apply_overrides(base_config, env_overrides)
            
            self.logger.info(f"Generated environment configuration for {environment_name}")
            return env_config
            
        except Exception as e:
            self.logger.error(f"Error getting environment configuration: {e}")
            return None
    
    def _apply_overrides(self, base_config: AnalysisConfig, 
                        overrides: Dict[str, Any]) -> AnalysisConfig:
        """Apply environment overrides to a base configuration.
        
        Args:
            base_config: Base AnalysisConfig
            overrides: Dictionary of overrides to apply
            
        Returns:
            New AnalysisConfig with overrides applied
        """
        # Create a copy of the base configuration
        import copy
        config_copy = copy.deepcopy(base_config)
        
        # Update last updated timestamp
        config_copy.last_updated = datetime.now().isoformat()
        
        # Apply parameter overrides
        if "parameters" in overrides:
            for param_name, param_value in overrides["parameters"].items():
                if param_name in config_copy.parameters:
                    # Update existing parameter
                    config_copy.parameters[param_name].value = param_value
                else:
                    # Create new parameter (this is a simplified approach)
                    new_param = AnalysisParameter(
                        name=param_name,
                        value=param_value,
                        description="Environment override parameter",
                        data_type="str",  # Default type
                        default_value=param_value
                    )
                    config_copy.parameters[param_name] = new_param
        
        # Apply other overrides
        for key, value in overrides.items():
            if key != "parameters" and hasattr(config_copy, key):
                setattr(config_copy, key, value)
                
        return config_copy


class ConfigurationVersionManager:
    """Manages configuration versioning for reproducible research."""
    
    def __init__(self, config_directory: Path, logger: logging.Logger = None):
        """Initialize the configuration version manager.
        
        Args:
            config_directory: Directory for storing configuration versions
            logger: Logger instance (optional)
        """
        self.config_directory = config_directory
        self.version_directory = config_directory / "versions"
        self.version_directory.mkdir(exist_ok=True)
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        
    def create_version(self, config: AnalysisConfig, version_notes: str = "") -> str:
        """Create a version of a configuration.
        
        Args:
            config: AnalysisConfig to version
            version_notes: Notes about this version
            
        Returns:
            Version identifier (hash-based)
        """
        try:
            # Create version metadata
            version_data = {
                "config": config.__dict__,
                "parameters": {name: param.__dict__ for name, param in config.parameters.items()},
                "version_notes": version_notes,
                "created_at": datetime.now().isoformat(),
                "hash": ""
            }
            
            # Generate hash of the configuration
            config_str = json.dumps(version_data, sort_keys=True, default=str)
            version_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
            version_data["hash"] = version_hash
            
            # Save version to file
            version_file = self.version_directory / f"{config.analysis_type}_{version_hash}.json"
            with open(version_file, 'w') as f:
                json.dump(version_data, f, indent=2, default=str)
                
            self.logger.info(f"Created configuration version {version_hash} for {config.analysis_type}")
            return version_hash
            
        except Exception as e:
            self.logger.error(f"Error creating configuration version: {e}")
            raise ConfigValidationError(f"Failed to create configuration version: {e}")
    
    def get_version(self, config_name: str, version_hash: str) -> Optional[AnalysisConfig]:
        """Retrieve a specific version of a configuration.
        
        Args:
            config_name: Name of the configuration
            version_hash: Version identifier
            
        Returns:
            AnalysisConfig for the specified version, or None if not found
        """
        try:
            version_file = self.version_directory / f"{config_name}_{version_hash}.json"
            if not version_file.exists():
                self.logger.warning(f"Configuration version {version_hash} for {config_name} not found")
                return None
                
            # Load version data
            with open(version_file, 'r') as f:
                version_data = json.load(f)
                
            # Reconstruct AnalysisConfig
            config_dict = version_data["config"]
            parameters_dict = version_data["parameters"]
            
            # Reconstruct parameters
            parameters = {}
            for name, param_dict in parameters_dict.items():
                # Remove class-specific fields
                param_dict_clean = {k: v for k, v in param_dict.items() 
                                  if not k.startswith('_') and k != '__dict__'}
                parameters[name] = AnalysisParameter(**param_dict_clean)
            
            # Remove parameter field from config dict and reconstruct
            config_dict_clean = {k: v for k, v in config_dict.items() 
                               if not k.startswith('_') and k != '__dict__' and k != 'parameters'}
            config_dict_clean["parameters"] = parameters
            
            config = AnalysisConfig(**config_dict_clean)
            
            self.logger.info(f"Retrieved configuration version {version_hash} for {config_name}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error retrieving configuration version: {e}")
            return None
    
    def list_versions(self, config_name: str) -> List[Dict[str, Any]]:
        """List all versions of a configuration.
        
        Args:
            config_name: Name of the configuration
            
        Returns:
            List of version information
        """
        versions = []
        try:
            # Find all version files for this configuration
            version_pattern = f"{config_name}_*.json"
            import glob
            version_files = glob.glob(str(self.version_directory / version_pattern))
            
            for version_file in version_files:
                try:
                    with open(version_file, 'r') as f:
                        version_data = json.load(f)
                        versions.append({
                            "hash": version_data["hash"],
                            "created_at": version_data["created_at"],
                            "notes": version_data["version_notes"]
                        })
                except Exception as e:
                    self.logger.warning(f"Error reading version file {version_file}: {e}")
                    
            self.logger.info(f"Found {len(versions)} versions for {config_name}")
            return versions
            
        except Exception as e:
            self.logger.error(f"Error listing configuration versions: {e}")
            return versions


class DynamicConfigurationUpdater:
    """Handles dynamic configuration updates during runtime."""
    
    def __init__(self, config_manager: AnalysisConfigurationManager,
                 validator: ConfigurationValidator, logger: logging.Logger = None):
        """Initialize the dynamic configuration updater.
        
        Args:
            config_manager: Analysis configuration manager
            validator: Configuration validator
            logger: Logger instance (optional)
        """
        self.config_manager = config_manager
        self.validator = validator
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.update_listeners = []  # List of callbacks for configuration updates
        
    def update_parameter(self, config_name: str, parameter_name: str, 
                        new_value: Any) -> bool:
        """Dynamically update a configuration parameter.
        
        Args:
            config_name: Name of the configuration
            parameter_name: Name of the parameter to update
            new_value: New value for the parameter
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get the current configuration
            config = self.config_manager.get_configuration(config_name)
            if config is None:
                self.logger.error(f"Configuration {config_name} not found")
                return False
                
            # Check if parameter exists
            if parameter_name not in config.parameters:
                self.logger.error(f"Parameter {parameter_name} not found in configuration {config_name}")
                return False
                
            # Create a temporary parameter with the new value for validation
            temp_param = config.parameters[parameter_name]
            original_value = temp_param.value
            temp_param.value = new_value
            
            # Validate the new parameter value
            validation_result = self.validator.validate_parameter(temp_param)
            if not validation_result["passed"]:
                self.logger.error(f"Invalid parameter value: {validation_result['errors']}")
                temp_param.value = original_value  # Restore original value
                return False
                
            # Update the parameter
            config.parameters[parameter_name].value = new_value
            config.last_updated = datetime.now().isoformat()
            
            # Notify listeners
            self._notify_listeners(config_name, parameter_name, new_value)
            
            self.logger.info(f"Updated parameter {parameter_name} in {config_name} to {new_value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating parameter {parameter_name}: {e}")
            return False
    
    def register_update_listener(self, callback) -> bool:
        """Register a callback to be notified of configuration updates.
        
        Args:
            callback: Function to call when configuration is updated
                        Should accept (config_name, parameter_name, new_value)
                        
        Returns:
            True if registration successful, False otherwise
        """
        try:
            self.update_listeners.append(callback)
            self.logger.info("Registered configuration update listener")
            return True
        except Exception as e:
            self.logger.error(f"Error registering update listener: {e}")
            return False
    
    def _notify_listeners(self, config_name: str, parameter_name: str, new_value: Any):
        """Notify all registered listeners of a configuration update.
        
        Args:
            config_name: Name of the updated configuration
            parameter_name: Name of the updated parameter
            new_value: New value of the parameter
        """
        for listener in self.update_listeners:
            try:
                listener(config_name, parameter_name, new_value)
            except Exception as e:
                self.logger.error(f"Error notifying listener: {e}")


# Convenience functions
def setup_standard_config_validation(logger: logging.Logger = None) -> ConfigurationValidator:
    """Set up standard configuration validation.
    
    Args:
        logger: Logger instance (optional)
        
    Returns:
        Configured ConfigurationValidator instance
    """
    return ConfigurationValidator(logger)


def setup_environment_config_manager(base_config_manager: AnalysisConfigurationManager,
                                   logger: logging.Logger = None) -> EnvironmentConfigurationManager:
    """Set up environment-specific configuration management.
    
    Args:
        base_config_manager: Base analysis configuration manager
        logger: Logger instance (optional)
        
    Returns:
        Configured EnvironmentConfigurationManager instance
    """
    return EnvironmentConfigurationManager(base_config_manager, logger)


def setup_config_version_manager(config_directory: Path,
                               logger: logging.Logger = None) -> ConfigurationVersionManager:
    """Set up configuration version management.
    
    Args:
        config_directory: Directory for storing configuration versions
        logger: Logger instance (optional)
        
    Returns:
        Configured ConfigurationVersionManager instance
    """
    return ConfigurationVersionManager(config_directory, logger)


def setup_dynamic_config_updater(config_manager: AnalysisConfigurationManager,
                               validator: ConfigurationValidator,
                               logger: logging.Logger = None) -> DynamicConfigurationUpdater:
    """Set up dynamic configuration updating.
    
    Args:
        config_manager: Analysis configuration manager
        validator: Configuration validator
        logger: Logger instance (optional)
        
    Returns:
        Configured DynamicConfigurationUpdater instance
    """
    return DynamicConfigurationUpdater(config_manager, validator, logger)


# Example usage:
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create configuration manager
    config_manager = AnalysisConfigurationManager()
    
    # Create validator
    validator = setup_standard_config_validation()
    
    # Validate a configuration
    config = config_manager.get_configuration("cost_driver_analysis")
    if config:
        validation_results = validator.validate_analysis_config(config)
        print(f"Validation passed: {validation_results['passed']}")
        if validation_results['errors']:
            print(f"Errors: {validation_results['errors']}")
    
    # Set up environment management
    env_manager = setup_environment_config_manager(config_manager)
    env_manager.add_environment("development", {
        "parameters": {
            "top_n_drivers": 5  # Override for development
        }
    })
    
    # Get environment-specific configuration
    dev_config = env_manager.get_environment_config("development", "cost_driver_analysis")
    if dev_config:
        print(f"Development config top_n_drivers: {dev_config.parameters['top_n_drivers'].value}")
    
    # Set up version management
    version_manager = setup_config_version_manager(config_manager.config_directory)
    if config:
        version_hash = version_manager.create_version(config, "Initial version for testing")
        print(f"Created version: {version_hash}")
        
        # Retrieve version
        retrieved_config = version_manager.get_version("cost_driver_analysis", version_hash)
        if retrieved_config:
            print(f"Retrieved version config: {retrieved_config.version}")
    
    # Set up dynamic updating
    updater = setup_dynamic_config_updater(config_manager, validator)
    if config:
        success = updater.update_parameter("cost_driver_analysis", "top_n_drivers", 15)
        print(f"Dynamic update success: {success}")