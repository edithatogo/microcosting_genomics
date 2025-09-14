"""Test cases for the Extensibility Framework module."""

import unittest
from unittest.mock import Mock
from pathlib import Path
import tempfile

from src.unimelb_phd_phase_1.extensibility_framework import (
    ExtensibilityFramework, Extension, AnalysisExtension, VisualizationExtension,
    ReportExtension, DataProcessorExtension, ExtensionMetadata
)
from src.unimelb_phd_phase_1.data_manager import DataManager


class TestExtensionMetadata(unittest.TestCase):
    """Test cases for ExtensionMetadata dataclass."""

    def test_extension_metadata_creation(self):
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
            extension_type="analysis"
        )
        
        self.assertEqual(metadata.name, "test_extension")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.description, "Test extension")
        self.assertEqual(metadata.author, "Test Author")
        self.assertEqual(metadata.license, "MIT")
        self.assertEqual(metadata.dependencies, ["dep1", "dep2"])
        self.assertEqual(metadata.tags, ["tag1", "tag2"])
        self.assertEqual(metadata.created_date, "2023-01-01T00:00:00")
        self.assertEqual(metadata.last_updated, "2023-01-01T00:00:00")
        self.assertEqual(metadata.extension_type, "analysis")


class TestExtension(unittest.TestCase):
    """Test cases for Extension base class."""

    def setUp(self):
        """Set up test fixtures."""
        self.extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension",
            author="Test Author",
            license="MIT",
            dependencies=["dep1"],
            tags=["tag1"]
        )

    def test_extension_initialization(self):
        """Test Extension initialization."""
        self.assertEqual(self.extension.metadata.name, "test_extension")
        self.assertEqual(self.extension.metadata.version, "1.0.0")
        self.assertEqual(self.extension.metadata.description, "Test extension")
        self.assertEqual(self.extension.metadata.author, "Test Author")
        self.assertEqual(self.extension.metadata.license, "MIT")
        self.assertEqual(self.extension.metadata.dependencies, ["dep1"])
        self.assertEqual(self.extension.metadata.tags, ["tag1"])
        self.assertFalse(self.extension.initialized)
        self.assertEqual(self.extension.config, {})

    def test_set_config(self):
        """Test setting extension configuration."""
        config = {"param1": "value1", "param2": 42}
        self.extension.set_config(config)
        self.assertEqual(self.extension.get_config(), config)

    def test_export_metadata(self):
        """Test exporting extension metadata."""
        metadata_dict = self.extension.export_metadata()
        self.assertIsInstance(metadata_dict, dict)
        self.assertEqual(metadata_dict["name"], "test_extension")

    def test_validate_dependencies(self):
        """Test validating extension dependencies."""
        available_extensions = ["dep1", "dep2", "dep3"]
        missing_deps = self.extension.validate_dependencies(available_extensions)
        self.assertEqual(missing_deps, [])  # All dependencies are available
        
        # Test with missing dependency
        extension_with_missing_dep = Extension(
            name="test_extension2",
            version="1.0.0",
            description="Test extension",
            dependencies=["dep1", "missing_dep"]
        )
        missing_deps = extension_with_missing_dep.validate_dependencies(available_extensions)
        self.assertEqual(missing_deps, ["missing_dep"])


class TestAnalysisExtension(unittest.TestCase):
    """Test cases for AnalysisExtension."""

    def test_analysis_extension_initialization(self):
        """Test AnalysisExtension initialization."""
        extension = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension"
        )
        
        self.assertEqual(extension.metadata.name, "test_analysis")
        self.assertEqual(extension.metadata.extension_type, "analysis")
        
        # Test that analyze method is abstract
        with self.assertRaises(NotImplementedError):
            extension.analyze("test_data")


class TestVisualizationExtension(unittest.TestCase):
    """Test cases for VisualizationExtension."""

    def test_visualization_extension_initialization(self):
        """Test VisualizationExtension initialization."""
        extension = VisualizationExtension(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization extension"
        )
        
        self.assertEqual(extension.metadata.name, "test_visualization")
        self.assertEqual(extension.metadata.extension_type, "visualization")
        
        # Test that visualize method is abstract
        with self.assertRaises(NotImplementedError):
            extension.visualize("test_data")


class TestReportExtension(unittest.TestCase):
    """Test cases for ReportExtension."""

    def test_report_extension_initialization(self):
        """Test ReportExtension initialization."""
        extension = ReportExtension(
            name="test_report",
            version="1.0.0",
            description="Test report extension"
        )
        
        self.assertEqual(extension.metadata.name, "test_report")
        self.assertEqual(extension.metadata.extension_type, "report")
        
        # Test that generate_report method is abstract
        with self.assertRaises(NotImplementedError):
            extension.generate_report("test_data")


class TestDataProcessorExtension(unittest.TestCase):
    """Test cases for DataProcessorExtension."""

    def test_data_processor_extension_initialization(self):
        """Test DataProcessorExtension initialization."""
        extension = DataProcessorExtension(
            name="test_processor",
            version="1.0.0",
            description="Test data processor extension"
        )
        
        self.assertEqual(extension.metadata.name, "test_processor")
        self.assertEqual(extension.metadata.extension_type, "data_processor")
        
        # Test that process method is abstract
        with self.assertRaises(NotImplementedError):
            extension.process("test_data")


class TestExtensibilityFramework(unittest.TestCase):
    """Test cases for ExtensibilityFramework."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.extension_dir = Path(self.temp_dir.name)
        
        self.mock_data_manager = Mock(spec=DataManager)
        self.framework = ExtensibilityFramework(
            extension_directory=self.extension_dir
        )
        self.framework.set_data_manager(self.mock_data_manager)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_framework_initialization(self):
        """Test ExtensibilityFramework initialization."""
        self.assertIsInstance(self.framework, ExtensibilityFramework)
        self.assertEqual(self.framework.extension_directory, self.extension_dir)
        self.assertEqual(self.framework.extensions, {})
        self.assertEqual(self.framework.config, {})

    def test_set_data_manager(self):
        """Test setting data manager."""
        self.assertEqual(self.framework.data_manager, self.mock_data_manager)

    def test_register_extension(self):
        """Test registering an extension."""
        extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension"
        )
        
        self.framework.register_extension(extension)
        self.assertIn("test_extension", self.framework.extensions)
        self.assertEqual(self.framework.extensions["test_extension"], extension)

    def test_get_extension(self):
        """Test getting an extension by name."""
        extension = Extension(
            name="test_extension",
            version="1.0.0",
            description="Test extension"
        )
        
        self.framework.register_extension(extension)
        retrieved_extension = self.framework.get_extension("test_extension")
        self.assertEqual(retrieved_extension, extension)
        
        # Test getting non-existent extension
        non_existent = self.framework.get_extension("non_existent")
        self.assertIsNone(non_existent)

    def test_list_extensions(self):
        """Test listing extensions."""
        extension1 = Extension(
            name="test_extension1",
            version="1.0.0",
            description="Test extension 1"
        )
        
        extension2 = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension"
        )
        
        self.framework.register_extension(extension1)
        self.framework.register_extension(extension2)
        
        extensions = self.framework.list_extensions()
        self.assertEqual(len(extensions), 2)
        
        # Check that both extensions are listed
        extension_names = [ext["name"] for ext in extensions]
        self.assertIn("test_extension1", extension_names)
        self.assertIn("test_analysis", extension_names)

    def test_get_extensions_by_type(self):
        """Test getting extensions by type."""
        analysis_ext = AnalysisExtension(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis extension"
        )
        
        viz_ext = VisualizationExtension(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization extension"
        )
        
        self.framework.register_extension(analysis_ext)
        self.framework.register_extension(viz_ext)
        
        analysis_extensions = self.framework.get_extensions_by_type("analysis")
        self.assertEqual(len(analysis_extensions), 1)
        self.assertEqual(analysis_extensions[0], analysis_ext)
        
        visualization_extensions = self.framework.get_extensions_by_type("visualization")
        self.assertEqual(len(visualization_extensions), 1)
        self.assertEqual(visualization_extensions[0], viz_ext)

    def test_validate_extension_dependencies(self):
        """Test validating extension dependencies."""
        # Create extensions with dependencies
        extension1 = Extension(
            name="extension1",
            version="1.0.0",
            description="Extension 1",
            dependencies=[]
        )
        
        extension2 = Extension(
            name="extension2",
            version="1.0.0",
            description="Extension 2",
            dependencies=["extension1"]  # Depends on extension1
        )
        
        extension3 = Extension(
            name="extension3",
            version="1.0.0",
            description="Extension 3",
            dependencies=["extension1", "missing_extension"]  # Depends on extension1 and missing extension
        )
        
        self.framework.register_extension(extension1)
        self.framework.register_extension(extension2)
        self.framework.register_extension(extension3)
        
        dependency_issues = self.framework.validate_extension_dependencies()
        self.assertIn("extension3", dependency_issues)
        self.assertEqual(dependency_issues["extension3"], ["missing_extension"])
        
        # extension1 and extension2 should have no issues
        self.assertNotIn("extension1", dependency_issues)
        self.assertNotIn("extension2", dependency_issues)

    def test_execute_extension_method(self):
        """Test executing an extension method."""
        # Create a mock extension with a test method
        class TestExtension(Extension):
            def __init__(self):
                super().__init__(
                    name="test_extension",
                    version="1.0.0",
                    description="Test extension"
                )
            
            def test_method(self, arg1, arg2="default"):
                return f"Called with {arg1} and {arg2}"
        
        extension = TestExtension()
        self.framework.register_extension(extension)
        
        # Execute the method
        result = self.framework.execute_extension_method(
            "test_extension", 
            "test_method", 
            "value1", 
            arg2="value2"
        )
        
        self.assertEqual(result, "Called with value1 and value2")

    def test_execute_extension_method_errors(self):
        """Test error handling in extension method execution."""
        # Test with non-existent extension
        with self.assertRaises(ValueError):
            self.framework.execute_extension_method("non_existent", "method")
        
        # Test with disabled extension
        extension = Extension(
            name="disabled_extension",
            version="1.0.0",
            description="Disabled extension"
        )
        extension.enabled = False
        self.framework.register_extension(extension)
        
        with self.assertRaises(ValueError):
            self.framework.execute_extension_method("disabled_extension", "method")
        
        # Test with non-existent method
        extension.enabled = True
        with self.assertRaises(AttributeError):
            self.framework.execute_extension_method("disabled_extension", "non_existent_method")


if __name__ == '__main__':
    unittest.main()