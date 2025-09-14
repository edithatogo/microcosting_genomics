"""Test cases for the Analysis Configuration module."""

import unittest
import tempfile
from pathlib import Path

from src.genomics_microcosting.analysis_config import (
    AnalysisParameter, AnalysisConfig, AnalysisConfigurationManager
)


class TestAnalysisParameter(unittest.TestCase):
    """Test cases for AnalysisParameter dataclass."""

    def test_analysis_parameter_creation(self):
        """Test AnalysisParameter creation."""
        parameter = AnalysisParameter(
            name="test_param",
            value=42,
            description="Test parameter",
            data_type="int",
            default_value=0,
            min_value=0,
            max_value=100,
            required=True,
            category="test"
        )
        
        self.assertEqual(parameter.name, "test_param")
        self.assertEqual(parameter.value, 42)
        self.assertEqual(parameter.description, "Test parameter")
        self.assertEqual(parameter.data_type, "int")
        self.assertEqual(parameter.default_value, 0)
        self.assertEqual(parameter.min_value, 0)
        self.assertEqual(parameter.max_value, 100)
        self.assertTrue(parameter.required)
        self.assertEqual(parameter.category, "test")


class TestAnalysisConfig(unittest.TestCase):
    """Test cases for AnalysisConfig dataclass."""

    def test_analysis_config_creation(self):
        """Test AnalysisConfig creation."""
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
            last_updated="2023-01-01T00:00:00",
            author="Test Author",
            tags=["test", "demo"]
        )
        
        self.assertEqual(config.analysis_type, "test_analysis")
        self.assertEqual(config.version, "1.0.0")
        self.assertEqual(config.description, "Test analysis configuration")
        self.assertEqual(config.parameters, parameters)
        self.assertEqual(config.created_date, "2023-01-01T00:00:00")
        self.assertEqual(config.last_updated, "2023-01-01T00:00:00")
        self.assertEqual(config.author, "Test Author")
        self.assertEqual(config.tags, ["test", "demo"])


class TestAnalysisConfigurationManager(unittest.TestCase):
    """Test cases for AnalysisConfigurationManager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        
        self.manager = AnalysisConfigurationManager(config_directory=self.config_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_manager_initialization(self):
        """Test AnalysisConfigurationManager initialization."""
        self.assertIsInstance(self.manager, AnalysisConfigurationManager)
        self.assertEqual(self.manager.config_directory, self.config_dir)
        self.assertGreater(len(self.manager.configs), 0)  # Should have default configs

    def test_list_configurations(self):
        """Test listing configurations."""
        configs = self.manager.list_configurations()
        self.assertIsInstance(configs, list)
        self.assertGreater(len(configs), 0)
        
        # Check that some expected configurations are present
        expected_configs = [
            "cost_driver_analysis", "dsa_analysis", "psa_analysis", 
            "voi_analysis", "budget_impact_analysis", "break_even_analysis",
            "cost_effectiveness_analysis", "benchmarking_analysis"
        ]
        for config_name in expected_configs:
            self.assertIn(config_name, configs)

    def test_get_configuration(self):
        """Test getting a configuration by name."""
        config = self.manager.get_configuration("cost_driver_analysis")
        self.assertIsNotNone(config)
        self.assertEqual(config.analysis_type, "cost_driver_analysis")
        
        # Test getting non-existent configuration
        non_existent = self.manager.get_configuration("non_existent")
        self.assertIsNone(non_existent)

    def test_get_parameter_value(self):
        """Test getting a parameter value."""
        # Test existing parameter
        value = self.manager.get_parameter_value("cost_driver_analysis", "top_n_drivers", 5)
        self.assertEqual(value, 10)  # Default value
        
        # Test non-existent parameter with default
        value = self.manager.get_parameter_value("cost_driver_analysis", "non_existent", 42)
        self.assertEqual(value, 42)

    def test_set_parameter_value(self):
        """Test setting a parameter value."""
        # Test setting valid value
        success = self.manager.set_parameter_value("cost_driver_analysis", "top_n_drivers", 15)
        self.assertTrue(success)
        
        # Verify the value was set
        value = self.manager.get_parameter_value("cost_driver_analysis", "top_n_drivers")
        self.assertEqual(value, 15)
        
        # Test setting invalid value (out of range)
        success = self.manager.set_parameter_value("cost_driver_analysis", "top_n_drivers", -5)
        self.assertFalse(success)  # Should fail due to min_value constraint
        
        # Test setting invalid value (wrong type)
        success = self.manager.set_parameter_value("cost_driver_analysis", "top_n_drivers", "invalid")
        self.assertFalse(success)  # Should fail due to type constraint

    def test_validate_configuration(self):
        """Test validating a configuration."""
        # Test valid configuration
        validation_results = self.manager.validate_configuration("cost_driver_analysis")
        self.assertIsInstance(validation_results, dict)
        self.assertIn("errors", validation_results)
        self.assertIn("warnings", validation_results)
        self.assertEqual(len(validation_results["errors"]), 0)  # Should be valid
        
        # Test non-existent configuration
        validation_results = self.manager.validate_configuration("non_existent")
        self.assertGreater(len(validation_results["errors"]), 0)

    def test_save_and_load_configuration(self):
        """Test saving and loading a configuration."""
        # Get an existing configuration
        original_config = self.manager.get_configuration("psa_analysis")
        self.assertIsNotNone(original_config)
        
        # Save it to a file
        config_file = self.config_dir / "test_psa_config.yaml"
        self.manager.save_configuration("psa_analysis", config_file)
        
        # Verify file was created
        self.assertTrue(config_file.exists())
        
        # Create a new manager and load the configuration
        new_manager = AnalysisConfigurationManager(config_directory=self.config_dir)
        loaded_config = new_manager.load_configuration("test_psa_config", config_file)
        
        # Verify the loaded configuration matches the original
        self.assertEqual(loaded_config.analysis_type, original_config.analysis_type)
        self.assertEqual(loaded_config.version, original_config.version)
        self.assertEqual(len(loaded_config.parameters), len(original_config.parameters))

    def test_generate_config_report(self):
        """Test generating a configuration report."""
        report = self.manager.generate_config_report()
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
        self.assertIn("Analysis Configuration Report", report)


if __name__ == '__main__':
    unittest.main()