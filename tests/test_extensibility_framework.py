# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Extensibility Framework module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pytest

from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.extensibility_framework import (
    AnalysisExtension,
    DataProcessorExtension,
    ExtensibilityFramework,
    Extension,
    ExtensionMetadata,
    ReportExtension,
    VisualizationExtension,
)
from tests.checks import require_equal, require_runtime_instance


class TestExtensionMetadata(unittest.TestCase):
    """Test cases for ExtensionMetadata dataclass."""

    def test_extension_metadata_creation(self) -> None:
        """Test ExtensionMetadata creation."""
        metadata = ExtensionMetadata(
            name="test_extension",
            version="1.0.0",
            description="Test extension",
            author="Test Author",
            license="MIT",
            dependencies=["dep1", "dep2"],
            tags=["tag1", "tag2"],
            created_date="2023-01-01T00:00:00",
            last_updated="2023-01-01T00:00:00",
            extension_type="analysis",
        )

        require_equal(metadata.name, "test_extension")
        require_equal(metadata.version, "1.0.0")
        require_equal(metadata.description, "Test extension")
        require_equal(metadata.author, "Test Author")
        require_equal(metadata.license, "MIT")
        require_equal(metadata.dependencies, ["dep1", "dep2"])
        require_equal(metadata.tags, ["tag1", "tag2"])
        require_equal(metadata.created_date, "2023-01-01T00:00:00")
        require_equal(metadata.last_updated, "2023-01-01T00:00:00")
        require_equal(metadata.extension_type, "analysis")


class TestExtension(unittest.TestCase):
    """Test cases for Extension base class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension",
            author="Test Author",
            license="MIT",
            dependencies=["dep1"],
            tags=["tag1"],
        )

    def test_extension_initialization(self) -> None:
        """Test Extension initialization."""
        if not ((self.extension.metadata.name) == ("test_extension")):
            raise AssertionError
        if not ((self.extension.metadata.version) == ("1.0.0")):
            raise AssertionError
        if not ((self.extension.metadata.description) == ("Test extension")):
            raise AssertionError
        if not ((self.extension.metadata.author) == ("Test Author")):
            raise AssertionError
        if not ((self.extension.metadata.license) == ("MIT")):
            raise AssertionError
        if not ((self.extension.metadata.dependencies) == (["dep1"])):
            raise AssertionError
        if not ((self.extension.metadata.tags) == (["tag1"])):
            raise AssertionError
        if self.extension.initialized:
            raise AssertionError
        if not ((self.extension.config) == ({})):
            raise AssertionError

    def test_set_config(self) -> None:
        """Test setting extension configuration."""
        config = {"param1": "value1", "param2": 42}
        self.extension.set_config(config)
        if not ((self.extension.get_config()) == (config)):
            raise AssertionError

    def test_export_metadata(self) -> None:
        """Test exporting extension metadata."""
        metadata_dict = self.extension.export_metadata()
        require_runtime_instance(metadata_dict, dict)
        if not ((metadata_dict["name"]) == ("test_extension")):
            raise AssertionError

    def test_validate_dependencies(self) -> None:
        """Test validating extension dependencies."""
        available_extensions = ["dep1", "dep2", "dep3"]
        missing_deps = self.extension.validate_dependencies(available_extensions)
        if not ((missing_deps) == ([])):
            raise AssertionError  # All dependencies are available

        # Test with missing dependency
        extension_with_missing_dep = Extension(
            name="test_extension2",
            version="1.0.0",
            description="Test extension",
            dependencies=["dep1", "missing_dep"],
        )
        missing_deps = extension_with_missing_dep.validate_dependencies(
            available_extensions,
        )
        if not ((missing_deps) == (["missing_dep"])):
            raise AssertionError


class TestAnalysisExtension(unittest.TestCase):
    """Test cases for AnalysisExtension."""

    def test_analysis_extension_initialization(self) -> None:
        """Test AnalysisExtension initialization."""
        extension = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension",
        )

        if not ((extension.metadata.name) == ("test_analysis")):
            raise AssertionError
        if not ((extension.metadata.extension_type) == ("analysis")):
            raise AssertionError

        # Test that analyze method is abstract
        with pytest.raises(NotImplementedError):
            extension.analyze("test_data")


class TestVisualizationExtension(unittest.TestCase):
    """Test cases for VisualizationExtension."""

    def test_visualization_extension_initialization(self) -> None:
        """Test VisualizationExtension initialization."""
        extension = VisualizationExtension(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization extension",
        )

        if not ((extension.metadata.name) == ("test_visualization")):
            raise AssertionError
        if not ((extension.metadata.extension_type) == ("visualization")):
            raise AssertionError

        # Test that visualize method is abstract
        with pytest.raises(NotImplementedError):
            extension.visualize("test_data")


class TestReportExtension(unittest.TestCase):
    """Test cases for ReportExtension."""

    def test_report_extension_initialization(self) -> None:
        """Test ReportExtension initialization."""
        extension = ReportExtension(
            name="test_report",
            version="1.0.0",
            description="Test report extension",
        )

        if not ((extension.metadata.name) == ("test_report")):
            raise AssertionError
        if not ((extension.metadata.extension_type) == ("report")):
            raise AssertionError

        # Test that generate_report method is abstract
        with pytest.raises(NotImplementedError):
            extension.generate_report("test_data")


class TestDataProcessorExtension(unittest.TestCase):
    """Test cases for DataProcessorExtension."""

    def test_data_processor_extension_initialization(self) -> None:
        """Test DataProcessorExtension initialization."""
        extension = DataProcessorExtension(
            name="test_processor",
            version="1.0.0",
            description="Test data processor extension",
        )

        if not ((extension.metadata.name) == ("test_processor")):
            raise AssertionError
        if not ((extension.metadata.extension_type) == ("data_processor")):
            raise AssertionError

        # Test that process method is abstract
        with pytest.raises(NotImplementedError):
            extension.process("test_data")


class TestExtensibilityFramework(unittest.TestCase):
    """Test cases for ExtensibilityFramework."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.extension_dir = Path(self.temp_dir.name)

        self.mock_data_manager = Mock(spec=DataManager)
        self.framework = ExtensibilityFramework(
            extension_directory=self.extension_dir,
        )
        self.framework.set_data_manager(self.mock_data_manager)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_framework_initialization(self) -> None:
        """Test ExtensibilityFramework initialization."""
        require_runtime_instance(self.framework, ExtensibilityFramework)
        if not ((self.framework.extension_directory) == (self.extension_dir)):
            raise AssertionError
        if not ((self.framework.extensions) == ({})):
            raise AssertionError
        if not ((self.framework.config) == ({})):
            raise AssertionError

    def test_set_data_manager(self) -> None:
        """Test setting data manager."""
        if not ((self.framework.data_manager) == (self.mock_data_manager)):
            raise AssertionError

    def test_register_extension(self) -> None:
        """Test registering an extension."""
        extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension",
        )

        self.framework.register_extension(extension)
        if ("test_extension") not in (self.framework.extensions):
            raise AssertionError
        if not ((self.framework.extensions["test_extension"]) == (extension)):
            raise AssertionError

    def test_get_extension(self) -> None:
        """Test getting an extension by name."""
        extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension",
        )

        self.framework.register_extension(extension)
        retrieved_extension = self.framework.get_extension("test_extension")
        if not ((retrieved_extension) == (extension)):
            raise AssertionError

        # Test getting non-existent extension
        non_existent = self.framework.get_extension("non_existent")
        if (non_existent) is not None:
            raise AssertionError

    def test_list_extensions(self) -> None:
        """Test listing extensions."""
        extension1 = Extension(
            name="test_extension1",
            version="1.0.0",
            description="Test extension 1",
        )

        extension2 = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension",
        )

        self.framework.register_extension(extension1)
        self.framework.register_extension(extension2)

        extensions = self.framework.list_extensions()
        require_equal(len(extensions), 2)

        # Check that both extensions are listed
        extension_names = [ext["name"] for ext in extensions]
        if ("test_extension1") not in (extension_names):
            raise AssertionError
        if ("test_analysis") not in (extension_names):
            raise AssertionError

    def test_get_extensions_by_type(self) -> None:
        """Test getting extensions by type."""
        analysis_ext = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension",
        )

        viz_ext = VisualizationExtension(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization extension",
        )

        self.framework.register_extension(analysis_ext)
        self.framework.register_extension(viz_ext)

        analysis_extensions = self.framework.get_extensions_by_type("analysis")
        if not ((len(analysis_extensions)) == (1)):
            raise AssertionError
        if not ((analysis_extensions[0]) == (analysis_ext)):
            raise AssertionError

        visualization_extensions = self.framework.get_extensions_by_type(
            "visualization",
        )
        if not ((len(visualization_extensions)) == (1)):
            raise AssertionError
        if not ((visualization_extensions[0]) == (viz_ext)):
            raise AssertionError

    def test_validate_extension_dependencies(self) -> None:
        """Test validating extension dependencies."""
        # Create extensions with dependencies
        extension1 = Extension(
            name="extension1",
            version="1.0.0",
            description="Extension 1",
            dependencies=[],
        )

        extension2 = Extension(
            name="extension2",
            version="1.0.0",
            description="Extension 2",
            dependencies=["extension1"],  # Depends on extension1
        )

        extension3 = Extension(
            name="extension3",
            version="1.0.0",
            description="Extension 3",
            dependencies=[
                "extension1",
                "missing_extension",
            ],  # Depends on extension1 and missing extension
        )

        self.framework.register_extension(extension1)
        self.framework.register_extension(extension2)
        self.framework.register_extension(extension3)

        dependency_issues = self.framework.validate_extension_dependencies()
        if ("extension3") not in (dependency_issues):
            raise AssertionError
        if not ((dependency_issues["extension3"]) == (["missing_extension"])):
            raise AssertionError

        # extension1 and extension2 should have no issues
        if not (("extension1") not in (dependency_issues)):
            raise AssertionError
        if not (("extension2") not in (dependency_issues)):
            raise AssertionError

    def test_execute_extension_method(self) -> None:
        """Test executing an extension method."""

        # Create a mock extension with a test method
        class TestExtension(Extension):
            def __init__(self) -> None:
                super().__init__(
                    name="test_extension",
                    version="1.0.0",
                    description="Test extension",
                )

            def test_method(self, arg1: str, arg2: str = "default") -> str:
                return f"Called with {arg1} and {arg2}"

        extension = TestExtension()
        self.framework.register_extension(extension)

        # Execute the method
        result = self.framework.execute_extension_method(
            "test_extension",
            "test_method",
            "value1",
            arg2="value2",
        )

        if not ((result) == ("Called with value1 and value2")):
            raise AssertionError

    def test_execute_extension_method_errors(self) -> None:
        """Test error handling in extension method execution."""
        # Test with non-existent extension
        with pytest.raises(ValueError, match="Extension non_existent not found"):
            self.framework.execute_extension_method("non_existent", "method")

        # Test with disabled extension
        extension = Extension(
            name="disabled_extension",
            version="1.0.0",
            description="Disabled extension",
        )
        extension.enabled = False
        self.framework.register_extension(extension)

        with pytest.raises(
            ValueError,
            match="Extension disabled_extension is not enabled",
        ):
            self.framework.execute_extension_method("disabled_extension", "method")

        # Test with non-existent method
        extension.enabled = True
        with pytest.raises(
            AttributeError,
            match="Extension disabled_extension does not have method "
            "non_existent_method",
        ):
            self.framework.execute_extension_method(
                "disabled_extension",
                "non_existent_method",
            )


if __name__ == "__main__":
    unittest.main()
