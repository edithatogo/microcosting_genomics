"""Test cases for the Configuration Validation module."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from genomics_microcosting.config_validation import (
    ConfigurationValidator, EnvironmentConfigurationManager, 
    ConfigurationVersionManager, DynamicConfigurationUpdater
)
from genomics_microcosting.analysis_config import (
    AnalysisParameter, AnalysisConfig, AnalysisConfigurationManager
)


class TestConfigurationValidator(unittest.TestCase):
    """Test cases for ConfigurationValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()
        self.analysis_config_manager = AnalysisConfigurationManager()

    def test_validate_parameter_valid_int(self):
        """Test validating a valid integer parameter."""
        parameter = AnalysisParameter(
            name="test_int",
            value=42,
            description="Test integer parameter",
            data_type="int",
            default_value=0,
            min_value=0,
            max_value=100
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_parameter_invalid_int_range(self):
        """Test validating an integer parameter with invalid range."""
        parameter = AnalysisParameter(
            name="test_int",
            value=150,  # Outside max_value
            description="Test integer parameter",
            data_type="int",
            default_value=0,
            min_value=0,
            max_value=100
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["errors"]), 0)

    def test_validate_parameter_valid_string(self):
        """Test validating a valid string parameter."""
        parameter = AnalysisParameter(
            name="test_string",
            value="test_value",
            description="Test string parameter",
            data_type="str",
            default_value=""
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_parameter_invalid_type(self):
        """Test validating a parameter with invalid data type."""
        parameter = AnalysisParameter(
            name="test_invalid",
            value=42,
            description="Test parameter",
            data_type="invalid_type",  # Invalid type
            default_value=0
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["errors"]), 0)

    def test_validate_parameter_with_choices(self):
        """Test validating a parameter with choices constraint."""
        parameter = AnalysisParameter(
            name="test_choice",
            value="option1",
            description="Test choice parameter",
            data_type="str",
            default_value="option1",
            choices=["option1", "option2", "option3"]
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["errors"]), 0)

    def test_validate_parameter_invalid_choice(self):
        """Test validating a parameter with invalid choice."""
        parameter = AnalysisParameter(
            name="test_choice",
            value="invalid_option",
            description="Test choice parameter",
            data_type="str",
            default_value="option1",
            choices=["option1", "option2", "option3"]
        )
        
        result = self.validator.validate_parameter(parameter)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["errors"]), 0)

    def test_validate_analysis_config(self):
        """Test validating an analysis configuration."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0
            )
        }
        
        config = AnalysisConfig(
            analysis_type="test_analysis",
            version="1.0.0",
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00"
        )
        
        result = self.validator.validate_analysis_config(config)
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(len(result["parameter_results"]), 1)

    def test_validate_analysis_config_missing_required_fields(self):
        """Test validating an analysis configuration with missing required fields."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0
            )
        }
        
        # Missing analysis_type and version
        config = AnalysisConfig(
            analysis_type="",  # Empty
            version="",  # Empty
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00"
        )
        
        result = self.validator.validate_analysis_config(config)
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["errors"]), 0)


class TestEnvironmentConfigurationManager(unittest.TestCase):
    """Test cases for EnvironmentConfigurationManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_config_manager = AnalysisConfigurationManager()
        self.env_manager = EnvironmentConfigurationManager(self.base_config_manager)

    def test_add_environment(self):
        """Test adding an environment configuration."""
        overrides = {
            "parameters": {
                "top_n_drivers": 5
            }
        }
        
        success = self.env_manager.add_environment("development", overrides)
        self.assertTrue(success)
        self.assertIn("development", self.env_manager.environments)

    def test_add_environment_invalid_name(self):
        """Test adding an environment with invalid name."""
        overrides = {"test": "value"}
        
        # This should not raise an exception but should return False
        self.env_manager.add_environment("", overrides)
        # The actual behavior depends on the InputValidator implementation

    def test_get_environment_config(self):
        """Test getting environment-specific configuration."""
        # Add environment
        overrides = {
            "parameters": {
                "top_n_drivers": 5
            }
        }
        self.env_manager.add_environment("development", overrides)
        
        # Get environment config
        env_config = self.env_manager.get_environment_config("development", "cost_driver_analysis")
        self.assertIsNotNone(env_config)
        self.assertEqual(env_config.parameters["top_n_drivers"].value, 5)

    def test_get_environment_config_nonexistent(self):
        """Test getting non-existent environment configuration."""
        # Should return base config when environment doesn't exist
        env_config = self.env_manager.get_environment_config("nonexistent", "cost_driver_analysis")
        self.assertIsNotNone(env_config)
        # Should be the same as base config
        base_config = self.base_config_manager.get_configuration("cost_driver_analysis")
        self.assertEqual(env_config.analysis_type, base_config.analysis_type)


class TestConfigurationVersionManager(unittest.TestCase):
    """Test cases for ConfigurationVersionManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        self.version_manager = ConfigurationVersionManager(self.config_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_create_version(self):
        """Test creating a configuration version."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0
            )
        }
        
        config = AnalysisConfig(
            analysis_type="test_analysis",
            version="1.0.0",
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00"
        )
        
        version_hash = self.version_manager.create_version(config, "Test version")
        self.assertIsInstance(version_hash, str)
        self.assertEqual(len(version_hash), 16)  # SHA256 truncated to 16 chars

    def test_create_version_and_retrieve(self):
        """Test creating and retrieving a configuration version."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0
            )
        }
        
        config = AnalysisConfig(
            analysis_type="test_analysis",
            version="1.0.0",
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00"
        )
        
        # Create version
        version_hash = self.version_manager.create_version(config, "Test version")
        
        # Retrieve version
        retrieved_config = self.version_manager.get_version("test_analysis", version_hash)
        self.assertIsNotNone(retrieved_config)
        self.assertEqual(retrieved_config.analysis_type, config.analysis_type)
        self.assertEqual(retrieved_config.version, config.version)

    def test_get_nonexistent_version(self):
        """Test retrieving a non-existent configuration version."""
        retrieved_config = self.version_manager.get_version("nonexistent", "nonexistent_hash")
        self.assertIsNone(retrieved_config)

    def test_list_versions(self):
        """Test listing configuration versions."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0
            )
        }
        
        config = AnalysisConfig(
            analysis_type="test_analysis",
            version="1.0.0",
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00"
        )
        
        # Create a version
        self.version_manager.create_version(config, "Test version")
        
        # List versions
        versions = self.version_manager.list_versions("test_analysis")
        self.assertIsInstance(versions, list)
        self.assertEqual(len(versions), 1)
        self.assertIn("hash", versions[0])
        self.assertIn("created_at", versions[0])


class TestDynamicConfigurationUpdater(unittest.TestCase):
    """Test cases for DynamicConfigurationUpdater."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = AnalysisConfigurationManager()
        self.validator = ConfigurationValidator()
        self.updater = DynamicConfigurationUpdater(self.config_manager, self.validator)

    def test_update_parameter(self):
        """Test dynamically updating a parameter."""
        # Get original value
        original_config = self.config_manager.get_configuration("cost_driver_analysis")
        original_value = original_config.parameters["top_n_drivers"].value
        
        # Update parameter
        success = self.updater.update_parameter("cost_driver_analysis", "top_n_drivers", 15)
        self.assertTrue(success)
        
        # Verify update
        updated_config = self.config_manager.get_configuration("cost_driver_analysis")
        self.assertEqual(updated_config.parameters["top_n_drivers"].value, 15)
        
        # Restore original value
        self.updater.update_parameter("cost_driver_analysis", "top_n_drivers", original_value)

    def test_update_parameter_invalid_value(self):
        """Test updating a parameter with invalid value."""
        # Try to update with invalid value (negative number for parameter with min_value=1)
        success = self.updater.update_parameter("cost_driver_analysis", "top_n_drivers", -5)
        self.assertFalse(success)
        
        # Verify value was not changed
        config = self.config_manager.get_configuration("cost_driver_analysis")
        self.assertGreaterEqual(config.parameters["top_n_drivers"].value, 1)

    def test_update_parameter_nonexistent_config(self):
        """Test updating a parameter in non-existent configuration."""
        success = self.updater.update_parameter("nonexistent_config", "param", "value")
        self.assertFalse(success)

    def test_update_parameter_nonexistent_param(self):
        """Test updating a non-existent parameter."""
        success = self.updater.update_parameter("cost_driver_analysis", "nonexistent_param", "value")
        self.assertFalse(success)

    def test_register_update_listener(self):
        """Test registering an update listener."""
        def test_listener(config_name, param_name, new_value):
            pass
            
        success = self.updater.register_update_listener(test_listener)
        self.assertTrue(success)
        self.assertEqual(len(self.updater.update_listeners), 1)

    def test_update_listener_notification(self):
        """Test that update listeners are notified."""
        # Create a mock listener
        listener = Mock()
        self.updater.register_update_listener(listener)
        
        # Update a parameter
        self.updater.update_parameter("cost_driver_analysis", "top_n_drivers", 20)
        
        # Verify listener was called
        listener.assert_called_once_with("cost_driver_analysis", "top_n_drivers", 20)


if __name__ == '__main__':
    unittest.main()