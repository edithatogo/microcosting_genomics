# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Analysis Configuration module."""

import tempfile
import unittest
from pathlib import Path

from genomics_microcosting.analysis_config import (
    AnalysisConfig,
    AnalysisConfigurationManager,
    AnalysisParameter,
)
from tests.checks import require_equal, require_runtime_instance


class TestAnalysisParameter(unittest.TestCase):
    """Test cases for AnalysisParameter dataclass."""

    def test_analysis_parameter_creation(self) -> None:
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
            category="test",
        )

        if not ((parameter.name) == ("test_param")):
            raise AssertionError
        require_equal(parameter.value, 42)
        if not ((parameter.description) == ("Test parameter")):
            raise AssertionError
        if not ((parameter.data_type) == ("int")):
            raise AssertionError
        if not ((parameter.default_value) == (0)):
            raise AssertionError
        if not ((parameter.min_value) == (0)):
            raise AssertionError
        require_equal(parameter.max_value, 100)
        if not (parameter.required):
            raise AssertionError
        if not ((parameter.category) == ("test")):
            raise AssertionError


class TestAnalysisConfig(unittest.TestCase):
    """Test cases for AnalysisConfig dataclass."""

    def test_analysis_config_creation(self) -> None:
        """Test AnalysisConfig creation."""
        parameters = {
            "param1": AnalysisParameter(
                name="param1",
                value=42,
                description="Test parameter",
                data_type="int",
                default_value=0,
            ),
        }

        config = AnalysisConfig(
            analysis_type="test_analysis",
            version="1.0.0",
            description="Test analysis configuration",
            parameters=parameters,
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00",
            author="Test Author",
            tags=["test", "demo"],
        )

        if not ((config.analysis_type) == ("test_analysis")):
            raise AssertionError
        if not ((config.version) == ("1.0.0")):
            raise AssertionError
        if not ((config.description) == ("Test analysis configuration")):
            raise AssertionError
        if not ((config.parameters) == (parameters)):
            raise AssertionError
        if not ((config.created_date) == ("2023-01-01T00:00:00")):
            raise AssertionError
        if not ((config.last_updated) == ("2023-01-01T00:00:00")):
            raise AssertionError
        if not ((config.author) == ("Test Author")):
            raise AssertionError
        if not ((config.tags) == (["test", "demo"])):
            raise AssertionError


class TestAnalysisConfigurationManager(unittest.TestCase):
    """Test cases for AnalysisConfigurationManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

        self.manager = AnalysisConfigurationManager(config_directory=self.config_dir)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_manager_initialization(self) -> None:
        """Test AnalysisConfigurationManager initialization."""
        require_runtime_instance(self.manager, AnalysisConfigurationManager)
        if not ((self.manager.config_directory) == (self.config_dir)):
            raise AssertionError
        if not ((len(self.manager.configs)) > (0)):
            raise AssertionError  # Should have default configs

    def test_list_configurations(self) -> None:
        """Test listing configurations."""
        configs = self.manager.list_configurations()
        require_runtime_instance(configs, list)
        if not ((len(configs)) > (0)):
            raise AssertionError

        # Check that some expected configurations are present
        expected_configs = [
            "cost_driver_analysis",
            "dsa_analysis",
            "psa_analysis",
            "voi_analysis",
            "budget_impact_analysis",
            "break_even_analysis",
            "cost_effectiveness_analysis",
            "benchmarking_analysis",
        ]
        for config_name in expected_configs:
            if (config_name) not in (configs):
                raise AssertionError

    def test_get_configuration(self) -> None:
        """Test getting a configuration by name."""
        config = self.manager.get_configuration("cost_driver_analysis")
        if not ((config) is not None):
            raise AssertionError
        if not ((config.analysis_type) == ("cost_driver_analysis")):
            raise AssertionError

        # Test getting non-existent configuration
        non_existent = self.manager.get_configuration("non_existent")
        if (non_existent) is not None:
            raise AssertionError

    def test_get_parameter_value(self) -> None:
        """Test getting a parameter value."""
        expected_parameter_value = 10
        # Test existing parameter
        value = self.manager.get_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            5,
        )
        if not ((value) == (expected_parameter_value)):
            raise AssertionError  # Default value

        # Test non-existent parameter with default
        value = self.manager.get_parameter_value(
            "cost_driver_analysis",
            "non_existent",
            42,
        )
        require_equal(value, 42)

    def test_set_parameter_value(self) -> None:
        """Test setting a parameter value."""
        # Test setting valid value
        success = self.manager.set_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            15,
        )
        if not (success):
            raise AssertionError

        # Verify the value was set
        value = self.manager.get_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
        )
        require_equal(value, 15)

        # Test setting invalid value (out of range)
        success = self.manager.set_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            -5,
        )
        if success:
            raise AssertionError  # Should fail due to min_value constraint

        # Test setting invalid value (wrong type)
        success = self.manager.set_parameter_value(
            "cost_driver_analysis",
            "top_n_drivers",
            "invalid",
        )
        if success:
            raise AssertionError  # Should fail due to type constraint

    def test_validate_configuration(self) -> None:
        """Test validating a configuration."""
        # Test valid configuration
        validation_results = self.manager.validate_configuration("cost_driver_analysis")
        require_runtime_instance(validation_results, dict)
        if ("errors") not in (validation_results):
            raise AssertionError
        if ("warnings") not in (validation_results):
            raise AssertionError
        if not ((len(validation_results["errors"])) == (0)):
            raise AssertionError  # Should be valid

        # Test non-existent configuration
        validation_results = self.manager.validate_configuration("non_existent")
        if not ((len(validation_results["errors"])) > (0)):
            raise AssertionError

    def test_save_and_load_configuration(self) -> None:
        """Test saving and loading a configuration."""
        # Get an existing configuration
        original_config = self.manager.get_configuration("psa_analysis")
        if not ((original_config) is not None):
            raise AssertionError

        # Save it to a file
        config_file = self.config_dir / "test_psa_config.yaml"
        self.manager.save_configuration("psa_analysis", config_file)

        # Verify file was created
        if not (config_file.exists()):
            raise AssertionError

        # Create a new manager and load the configuration
        new_manager = AnalysisConfigurationManager(config_directory=self.config_dir)
        loaded_config = new_manager.load_configuration("test_psa_config", config_file)

        # Verify the loaded configuration matches the original
        if not ((loaded_config.analysis_type) == (original_config.analysis_type)):
            raise AssertionError
        if not ((loaded_config.version) == (original_config.version)):
            raise AssertionError
        if not ((len(loaded_config.parameters)) == (len(original_config.parameters))):
            raise AssertionError

    def test_generate_config_report(self) -> None:
        """Test generating a configuration report."""
        report = self.manager.generate_config_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError
        if ("Analysis Configuration Report") not in (report):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
