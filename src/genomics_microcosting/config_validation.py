# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Configuration validation for genomics microcosting analysis.

This module provides comprehensive configuration validation capabilities including
parameter validation, environment-specific configurations, configuration versioning,
and dynamic configuration updates.
"""

import hashlib
import json
import logging
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import SupportsIndex, SupportsInt, TypedDict

from pydantic import TypeAdapter

from .analysis_config import (
    AnalysisConfig,
    AnalysisConfigurationManager,
    AnalysisParameter,
    load_analysis_configuration,
)
from .input_validation import InputValidator, ValidationError
from .logging_config import get_logger

logger = get_logger(__name__)


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""


class _ValidationResult(TypedDict):
    passed: bool
    errors: list[str]
    warnings: list[str]


class ParameterValidationResult(_ValidationResult):
    """Validation of a single parameter with its name."""

    parameter: str


class ConfigurationValidationResult(_ValidationResult):
    """Configuration-wide validation and individual parameter results."""

    config: str
    parameter_results: list[ParameterValidationResult]


class VersionInfo(TypedDict):
    """Saved configuration version metadata."""

    hash: str
    created_at: str
    notes: str


class _SavedVersion(TypedDict):
    hash: str
    created_at: str
    version_notes: str


_MAPPING = TypeAdapter(dict[str, object])
_SAVED_VERSION = TypeAdapter(_SavedVersion)
type UpdateListener = Callable[[str, str, object], object]


class ConfigurationValidator:
    """Validates configuration parameters and structures."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the configuration validator.

        Args:
            logger: Logger instance (optional)

        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.validator = InputValidator(self.logger)
        self.analysis_config_manager = AnalysisConfigurationManager()

    def validate_parameter(
        self,
        parameter: AnalysisParameter,
    ) -> ParameterValidationResult:
        """Validate a single parameter.

        Args:
            parameter: AnalysisParameter to validate

        Returns:
            Dictionary with validation results

        """
        results: ParameterValidationResult = {
            "parameter": parameter.name,
            "passed": True,
            "errors": [],
            "warnings": [],
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
                results["errors"].append(
                    (
                        f"Value {parameter.value} not in "
                        f"allowed choices: {parameter.choices}"
                    ),
                )

        except (ValidationError, ValueError, TypeError, OverflowError) as e:
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
        value = parameter.value
        try:
            match parameter.data_type:
                case "int" | "float":
                    valid = self._validate_number(parameter)
                case "str":
                    valid = self.validator.validate_string_value(
                        value,
                        allow_empty=True,
                    )
                case "bool":
                    if isinstance(value, str):
                        valid = value.lower() in {"true", "false", "1", "0"}
                    else:
                        bool(value)
                        valid = True
                case "list":
                    valid = value is None or isinstance(value, list)
                case "dict":
                    valid = value is None or isinstance(value, dict)
                case _:
                    valid = False
        except ValidationError, ValueError, TypeError, OverflowError:
            return False
        else:
            return valid

    def _validate_number(self, parameter: AnalysisParameter) -> bool:
        value = parameter.value
        self.validator.validate_numeric_value(value, allow_none=not parameter.required)
        if parameter.data_type != "int" or value is None or isinstance(value, int):
            return True
        if isinstance(value, (str, bytes, bytearray, SupportsInt, SupportsIndex)):
            int(value)
            return True
        return False

    def _validate_constraints(self, parameter: AnalysisParameter) -> bool:
        """Validate parameter value against constraints.

        Args:
            parameter: AnalysisParameter to validate

        Returns:
            True if valid, False otherwise

        """
        if parameter.value is None:
            return not parameter.required

        try:
            # Validate min/max for numeric types
            if parameter.data_type in ("int", "float"):
                if parameter.min_value is not None:
                    self.validator.validate_numeric_value(
                        parameter.value,
                        min_value=parameter.min_value,
                    )
                if parameter.max_value is not None:
                    self.validator.validate_numeric_value(
                        parameter.value,
                        max_value=parameter.max_value,
                    )

        except ValidationError:
            return False
        else:
            return True

    def validate_analysis_config(
        self,
        config: AnalysisConfig,
    ) -> ConfigurationValidationResult:
        """Validate an entire analysis configuration.

        Args:
            config: AnalysisConfig to validate

        Returns:
            Dictionary with validation results

        """
        results: ConfigurationValidationResult = {
            "config": config.analysis_type,
            "passed": True,
            "errors": [],
            "warnings": [],
            "parameter_results": [],
        }

        try:
            # Validate each parameter
            for param_name, parameter in config.parameters.items():
                param_result = self.validate_parameter(parameter)
                results["parameter_results"].append(param_result)

                if not param_result["passed"]:
                    results["passed"] = False
                    results["errors"].extend(
                        [f"{param_name}: {error}" for error in param_result["errors"]],
                    )

            # Validate required fields
            if not config.analysis_type:
                results["passed"] = False
                results["errors"].append("Analysis type is required")

            if not config.version:
                results["passed"] = False
                results["errors"].append("Version is required")

            if not config.description:
                results["warnings"].append("Description is recommended")

        except (ValidationError, ValueError, TypeError, OverflowError) as e:
            results["passed"] = False
            results["errors"].append(f"Error during configuration validation: {e}")

        return results


class EnvironmentConfigurationManager:
    """Manages environment-specific configurations."""

    def __init__(
        self,
        base_config_manager: AnalysisConfigurationManager,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the environment configuration manager.

        Args:
            base_config_manager: Base analysis configuration manager
            logger: Logger instance (optional)

        """
        self.base_config_manager = base_config_manager
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.environments: dict[str, Mapping[str, object]] = {}

    def add_environment(
        self,
        environment_name: str,
        config_overrides: Mapping[str, object],
    ) -> bool:
        """Add or update an environment configuration.

        Args:
            environment_name: Environment name such as development or testing
            config_overrides: Configuration overrides for this environment

        Returns:
            True if successful, False otherwise

        """
        try:
            self.validator = InputValidator(self.logger)
            self.validator.validate_string_value(environment_name, max_length=50)

            # Store the environment configuration
            self.environments[environment_name] = config_overrides
            self.logger.info("Added environment configuration: %s", environment_name)
        except ValidationError:
            self.logger.exception("Invalid environment name")
            return False
        except Exception:
            self.logger.exception(
                "Error adding environment %s",
                environment_name,
            )
            return False
        else:
            return True

    def get_environment_config(
        self,
        environment_name: str,
        base_config_name: str,
    ) -> AnalysisConfig | None:
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
                self.logger.warning("Base configuration %s not found", base_config_name)
                return None

            # Check if environment exists
            if environment_name not in self.environments:
                self.logger.warning("Environment %s not found", environment_name)
                return base_config  # Return base config if no environment overrides

            # Apply environment overrides
            env_overrides = self.environments[environment_name]
            env_config = self._apply_overrides(base_config, env_overrides)

            self.logger.info(
                "Generated environment configuration for %s",
                environment_name,
            )

        except Exception:
            self.logger.exception("Error getting environment configuration")
            return None
        else:
            return env_config

    def _apply_overrides(
        self,
        base_config: AnalysisConfig,
        overrides: Mapping[str, object],
    ) -> AnalysisConfig:
        """Apply environment overrides to a base configuration.

        Args:
            base_config: Base AnalysisConfig
            overrides: Dictionary of overrides to apply

        Returns:
            New AnalysisConfig with overrides applied

        """
        config_copy = deepcopy(base_config)

        # Update last updated timestamp
        config_copy.last_updated = datetime.now(UTC).isoformat()

        # Apply parameter overrides
        if "parameters" in overrides:
            parameter_overrides = _MAPPING.validate_python(
                overrides["parameters"],
                strict=True,
            )
            for param_name, param_value in parameter_overrides.items():
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
                        default_value=param_value,
                    )
                    config_copy.parameters[param_name] = new_param

        # Apply other overrides
        for key, value in overrides.items():
            if key != "parameters" and hasattr(config_copy, key):
                setattr(config_copy, key, value)

        return config_copy


class ConfigurationVersionManager:
    """Manages configuration versioning for reproducible research."""

    def __init__(
        self,
        config_directory: Path,
        logger: logging.Logger | None = None,
    ) -> None:
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
                "parameters": {
                    name: param.__dict__ for name, param in config.parameters.items()
                },
                "version_notes": version_notes,
                "created_at": datetime.now(UTC).isoformat(),
                "hash": "",
            }

            # Generate hash of the configuration
            config_str = json.dumps(version_data, sort_keys=True, default=str)
            version_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
            version_data["hash"] = version_hash

            # Save version to file
            version_file = (
                self.version_directory / f"{config.analysis_type}_{version_hash}.json"
            )
            with Path(version_file).open("w") as f:
                json.dump(version_data, f, indent=2, default=str)

            self.logger.info(
                "Created configuration version %s for %s",
                version_hash,
                config.analysis_type,
            )

        except Exception as e:
            self.logger.exception("Error creating configuration version")
            message = f"Failed to create configuration version: {e}"
            raise ConfigValidationError(message) from e
        else:
            return version_hash

    def get_version(self, config_name: str, version_hash: str) -> AnalysisConfig | None:
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
                self.logger.warning(
                    "Configuration version %s for %s not found",
                    version_hash,
                    config_name,
                )
                return None

            # Load version data
            with Path(version_file).open() as f:
                version_data = json.load(f)

            version_fields = _MAPPING.validate_python(version_data, strict=True)
            config_fields = _MAPPING.validate_python(
                version_fields["config"],
                strict=True,
            )
            config_fields["parameters"] = version_fields["parameters"]
            config = load_analysis_configuration(config_fields)

            self.logger.info(
                "Retrieved configuration version %s for %s",
                version_hash,
                config_name,
            )

        except Exception:
            self.logger.exception("Error retrieving configuration version")
            return None
        else:
            return config

    def list_versions(self, config_name: str) -> list[VersionInfo]:
        """List all versions of a configuration.

        Args:
            config_name: Name of the configuration

        Returns:
            List of version information

        """
        versions: list[VersionInfo] = []
        try:
            version_pattern = f"{config_name}_*.json"
            for version_file in self.version_directory.glob(version_pattern):
                try:
                    with Path(version_file).open() as f:
                        version_data = _SAVED_VERSION.validate_json(
                            f.read(),
                            strict=True,
                        )
                    versions.append(
                        {
                            "hash": version_data["hash"],
                            "created_at": version_data["created_at"],
                            "notes": version_data["version_notes"],
                        },
                    )
                except (OSError, ValueError, TypeError, KeyError) as e:
                    self.logger.warning(
                        "Error reading version file %s: %s",
                        version_file,
                        e,
                    )

            self.logger.info("Listed configuration versions")

        except Exception:
            self.logger.exception("Error listing configuration versions")
            return versions
        else:
            return versions


class DynamicConfigurationUpdater:
    """Handles dynamic configuration updates during runtime."""

    def __init__(
        self,
        config_manager: AnalysisConfigurationManager,
        validator: ConfigurationValidator,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the dynamic configuration updater.

        Args:
            config_manager: Analysis configuration manager
            validator: Configuration validator
            logger: Logger instance (optional)

        """
        self.config_manager = config_manager
        self.validator = validator
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.update_listeners: list[UpdateListener] = []

    def update_parameter(
        self,
        config_name: str,
        parameter_name: str,
        new_value: object,
    ) -> bool:
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
                self.logger.error("Configuration %s not found", config_name)
                return False

            # Check if parameter exists
            if parameter_name not in config.parameters:
                self.logger.error(
                    "Parameter %s not found in configuration %s",
                    parameter_name,
                    config_name,
                )
                return False

            # Create a temporary parameter with the new value for validation
            temp_param = replace(config.parameters[parameter_name], value=new_value)

            # Validate the new parameter value
            validation_result = self.validator.validate_parameter(temp_param)
            if not validation_result["passed"]:
                self.logger.error(
                    "Invalid parameter value: %s",
                    validation_result["errors"],
                )
                return False

            # Update the parameter
            config.parameters[parameter_name].value = new_value
            config.last_updated = datetime.now(UTC).isoformat()

            # Notify listeners
            self._notify_listeners(config_name, parameter_name, new_value)

            self.logger.info(
                "Updated parameter %s in %s to %s",
                parameter_name,
                config_name,
                new_value,
            )

        except Exception:
            self.logger.exception("Error updating parameter %s", parameter_name)
            return False
        else:
            return True

    def register_update_listener(self, callback: UpdateListener) -> bool:
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
        except Exception:
            self.logger.exception("Error registering update listener")
            return False
        else:
            return True

    def _notify_listeners(
        self,
        config_name: str,
        parameter_name: str,
        new_value: object,
    ) -> None:
        """Notify all registered listeners of a configuration update.

        Args:
            config_name: Name of the updated configuration
            parameter_name: Name of the updated parameter
            new_value: New value of the parameter

        """
        for listener in self.update_listeners:
            try:
                listener(config_name, parameter_name, new_value)
            except Exception:
                self.logger.exception("Error notifying listener")


# Convenience functions
def setup_standard_config_validation(
    logger: logging.Logger | None = None,
) -> ConfigurationValidator:
    """Set up standard configuration validation.

    Args:
        logger: Logger instance (optional)

    Returns:
        Configured ConfigurationValidator instance

    """
    return ConfigurationValidator(logger)


def setup_environment_config_manager(
    base_config_manager: AnalysisConfigurationManager,
    logger: logging.Logger | None = None,
) -> EnvironmentConfigurationManager:
    """Set up environment-specific configuration management.

    Args:
        base_config_manager: Base analysis configuration manager
        logger: Logger instance (optional)

    Returns:
        Configured EnvironmentConfigurationManager instance

    """
    return EnvironmentConfigurationManager(base_config_manager, logger)


def setup_config_version_manager(
    config_directory: Path,
    logger: logging.Logger | None = None,
) -> ConfigurationVersionManager:
    """Set up configuration version management.

    Args:
        config_directory: Directory for storing configuration versions
        logger: Logger instance (optional)

    Returns:
        Configured ConfigurationVersionManager instance

    """
    return ConfigurationVersionManager(config_directory, logger)


def setup_dynamic_config_updater(
    config_manager: AnalysisConfigurationManager,
    validator: ConfigurationValidator,
    logger: logging.Logger | None = None,
) -> DynamicConfigurationUpdater:
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
    logging.basicConfig(level=logging.INFO)

    # Create configuration manager
    config_manager = AnalysisConfigurationManager()

    # Create validator
    validator = setup_standard_config_validation()

    # Validate a configuration
    config = config_manager.get_configuration("cost_driver_analysis")
    if config:
        validation_results = validator.validate_analysis_config(config)
        logger.info("%s", f"Validation passed: {validation_results['passed']}")
        if validation_results["errors"]:
            logger.info("%s", f"Errors: {validation_results['errors']}")

    # Set up environment management
    env_manager = setup_environment_config_manager(config_manager)
    env_manager.add_environment(
        "development",
        {
            "parameters": {
                "top_n_drivers": 5,  # Override for development
            },
        },
    )

    # Get environment-specific configuration
    dev_config = env_manager.get_environment_config(
        "development",
        "cost_driver_analysis",
    )
    if dev_config:
        logger.info(
            "%s",
            (
                f"Development config top_n_drivers: "
                f"{dev_config.parameters['top_n_drivers'].value}"
            ),
        )

    # Set up version management
    version_manager = setup_config_version_manager(config_manager.config_directory)
    if config:
        version_hash = version_manager.create_version(
            config,
            "Initial version for testing",
        )
        logger.info("%s", f"Created version: {version_hash}")

        # Retrieve version
        retrieved_config = version_manager.get_version(
            "cost_driver_analysis",
            version_hash,
        )
        if retrieved_config:
            logger.info("%s", f"Retrieved version config: {retrieved_config.version}")

    # Set up dynamic updating
    updater = setup_dynamic_config_updater(config_manager, validator)
    if config:
        success = updater.update_parameter("cost_driver_analysis", "top_n_drivers", 15)
        logger.info("%s", f"Dynamic update success: {success}")
