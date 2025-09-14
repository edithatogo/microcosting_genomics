"""Extensibility Framework for microcosting analysis.

This module provides a comprehensive framework for extending the microcosting analysis
with custom analyses, visualizations, and plugins.
"""

import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from abc import abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

from .logging_config import get_logger
from .data_manager import DataManager
from .plugin_system import Plugin


logger = get_logger(__name__)


@dataclass
class ExtensionMetadata:
    """Metadata for an extension."""
    name: str
    version: str
    description: str
    author: str
    license: str
    dependencies: List[str]
    tags: List[str]
    created_date: str
    last_updated: str
    extension_type: str  # 'analysis', 'visualization', 'report', 'data_processor', etc.


class Extension(Plugin):
    """Base class for all extensions."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None, extension_type: str = "generic"):
        """Initialize an extension.
        
        Args:
            name: Extension name
            version: Extension version
            description: Extension description
            author: Extension author
            license: Extension license
            dependencies: Extension dependencies
            tags: Extension tags for categorization
            extension_type: Type of extension
        """
        super().__init__(name, version, description)
        self.metadata = ExtensionMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            license=license,
            dependencies=dependencies or [],
            tags=tags or [],
            created_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            extension_type=extension_type
        )
        self.initialized = False
        self.config: Dict[str, Any] = {}
        self.data_manager: Optional[DataManager] = None
    
    def set_data_manager(self, data_manager: DataManager) -> None:
        """Set the data manager for this extension.
        
        Args:
            data_manager: DataManager instance
        """
        self.data_manager = data_manager
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set extension configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.metadata.last_updated = datetime.now().isoformat()
    
    def get_config(self) -> Dict[str, Any]:
        """Get extension configuration.
        
        Returns:
            Configuration dictionary
        """
        return self.config
    
    def export_metadata(self) -> Dict[str, Any]:
        """Export extension metadata.
        
        Returns:
            Extension metadata as dictionary
        """
        return asdict(self.metadata)
    
    def validate_dependencies(self, available_extensions: List[str]) -> List[str]:
        """Validate extension dependencies.
        
        Args:
            available_extensions: List of available extension names
            
        Returns:
            List of missing dependencies
        """
        missing_deps = []
        for dep in self.metadata.dependencies:
            if dep not in available_extensions:
                missing_deps.append(dep)
        return missing_deps


class AnalysisExtension(Extension):
    """Extension for custom analysis functionality."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize an analysis extension.
        
        Args:
            name: Extension name
            version: Extension version
            description: Extension description
            author: Extension author
            license: Extension license
            dependencies: Extension dependencies
            tags: Extension tags for categorization
        """
        super().__init__(name, version, description, author, license, dependencies, tags, "analysis")
    
    @abstractmethod
    def analyze(self, data: Any, **kwargs) -> Any:
        """Perform analysis on data.
        
        Args:
            data: Input data
            **kwargs: Additional analysis parameters
            
        Returns:
            Analysis results
        """
        raise NotImplementedError("Subclasses must implement analyze method")


class VisualizationExtension(Extension):
    """Extension for custom visualization functionality."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize a visualization extension.
        
        Args:
            name: Extension name
            version: Extension version
            description: Extension description
            author: Extension author
            license: Extension license
            dependencies: Extension dependencies
            tags: Extension tags for categorization
        """
        super().__init__(name, version, description, author, license, dependencies, tags, "visualization")
    
    @abstractmethod
    def visualize(self, data: Any, **kwargs) -> Any:
        """Create visualization of data.
        
        Args:
            data: Input data
            **kwargs: Additional visualization parameters
            
        Returns:
            Visualization object
        """
        raise NotImplementedError("Subclasses must implement visualize method")


class ReportExtension(Extension):
    """Extension for custom report generation functionality."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize a report extension.
        
        Args:
            name: Extension name
            version: Extension version
            description: Extension description
            author: Extension author
            license: Extension license
            dependencies: Extension dependencies
            tags: Extension tags for categorization
        """
        super().__init__(name, version, description, author, license, dependencies, tags, "report")
    
    @abstractmethod
    def generate_report(self, data: Any, output_format: str = "markdown", **kwargs) -> str:
        """Generate report.
        
        Args:
            data: Input data
            output_format: Output format (markdown, html, pdf, etc.)
            **kwargs: Additional report parameters
            
        Returns:
            Generated report
        """
        raise NotImplementedError("Subclasses must implement generate_report method")


class DataProcessorExtension(Extension):
    """Extension for custom data processing functionality."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize a data processor extension.
        
        Args:
            name: Extension name
            version: Extension version
            description: Extension description
            author: Extension author
            license: Extension license
            dependencies: Extension dependencies
            tags: Extension tags for categorization
        """
        super().__init__(name, version, description, author, license, dependencies, tags, "data_processor")
    
    @abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """Process data.
        
        Args:
            data: Input data
            **kwargs: Additional processing parameters
            
        Returns:
            Processed data
        """
        raise NotImplementedError("Subclasses must implement process method")


class ExtensibilityFramework:
    """Framework for managing extensions and providing extensibility features."""
    
    def __init__(self, extension_directory: Optional[Path] = None, 
                 config_file: Optional[Path] = None):
        """Initialize the extensibility framework.
        
        Args:
            extension_directory: Directory to search for extensions
            config_file: Configuration file for extension settings
        """
        self.extensions: Dict[str, Extension] = {}
        self.extension_directory = extension_directory or Path(__file__).resolve().parents[0] / "extensions"
        self.extension_directory.mkdir(exist_ok=True)
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.data_manager: Optional[DataManager] = None
        
        # Load configuration if provided
        if self.config_file and self.config_file.exists():
            self.load_config()
        
        logger.info(f"ExtensibilityFramework initialized with directory: {self.extension_directory}")
    
    def set_data_manager(self, data_manager: DataManager) -> None:
        """Set the data manager for all extensions.
        
        Args:
            data_manager: DataManager instance
        """
        self.data_manager = data_manager
        # Set data manager for all existing extensions
        for extension in self.extensions.values():
            extension.set_data_manager(data_manager)
    
    def load_config(self) -> None:
        """Load framework configuration."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def save_config(self) -> None:
        """Save framework configuration."""
        if self.config_file:
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
                logger.info(f"Saved configuration to {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to save configuration: {e}")
    
    def load_extension(self, extension_path: Path) -> Extension:
        """Load an extension from a file.
        
        Args:
            extension_path: Path to the extension file
            
        Returns:
            Loaded extension instance
            
        Raises:
            ImportError: If extension cannot be loaded
        """
        logger.info(f"Loading extension from {extension_path}")
        
        # Load the module
        spec = importlib.util.spec_from_file_location(extension_path.stem, extension_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load extension from {extension_path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the extension class (should be the only class that inherits from Extension)
        extension_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Extension) and 
                attr != Extension and 
                attr != AnalysisExtension and 
                attr != VisualizationExtension and 
                attr != ReportExtension and 
                attr != DataProcessorExtension):
                extension_class = attr
                break
        
        if extension_class is None:
            raise ImportError(f"No valid extension class found in {extension_path}")
        
        # Create extension instance
        try:
            extension_instance = extension_class()
        except Exception as e:
            raise ImportError(f"Failed to instantiate extension from {extension_path}: {e}")
        
        # Set data manager if available
        if self.data_manager:
            extension_instance.set_data_manager(self.data_manager)
        
        logger.info(f"Loaded extension: {extension_instance.metadata.name} v{extension_instance.metadata.version}")
        return extension_instance
    
    def discover_extensions(self) -> List[Path]:
        """Discover extension files in the extension directory.
        
        Returns:
            List of extension file paths
        """
        extension_files = []
        for file_path in self.extension_directory.glob("*.py"):
            if file_path.name != "__init__.py":
                extension_files.append(file_path)
        
        logger.info(f"Discovered {len(extension_files)} extension files")
        return extension_files
    
    def register_extension(self, extension: Extension) -> None:
        """Register an extension.
        
        Args:
            extension: Extension instance to register
        """
        if extension.metadata.name in self.extensions:
            logger.warning(f"Extension {extension.metadata.name} already registered, replacing")
        
        self.extensions[extension.metadata.name] = extension
        logger.info(f"Registered extension: {extension.metadata.name}")
    
    def load_all_extensions(self) -> None:
        """Load and register all extensions in the extension directory."""
        extension_files = self.discover_extensions()
        
        for extension_file in extension_files:
            try:
                extension = self.load_extension(extension_file)
                self.register_extension(extension)
                if extension.enabled:
                    extension.initialize()
            except Exception as e:
                logger.error(f"Failed to load extension {extension_file}: {e}")
    
    def get_extension(self, name: str) -> Optional[Extension]:
        """Get a registered extension by name.
        
        Args:
            name: Extension name
            
        Returns:
            Extension instance or None if not found
        """
        return self.extensions.get(name)
    
    def list_extensions(self) -> List[Dict[str, Any]]:
        """List all registered extensions.
        
        Returns:
            List of extension information
        """
        extension_info = []
        for name, extension in self.extensions.items():
            extension_info.append({
                "name": extension.metadata.name,
                "version": extension.metadata.version,
                "description": extension.metadata.description,
                "author": extension.metadata.author,
                "license": extension.metadata.license,
                "type": extension.metadata.extension_type,
                "tags": extension.metadata.tags,
                "enabled": extension.enabled
            })
        return extension_info
    
    def get_extensions_by_type(self, extension_type: str) -> List[Extension]:
        """Get extensions by type.
        
        Args:
            extension_type: Type of extensions to retrieve
            
        Returns:
            List of extensions of the specified type
        """
        extensions = []
        for extension in self.extensions.values():
            if extension.metadata.extension_type == extension_type:
                extensions.append(extension)
        return extensions
    
    def validate_extension_dependencies(self) -> Dict[str, List[str]]:
        """Validate dependencies for all extensions.
        
        Returns:
            Dictionary mapping extension names to lists of missing dependencies
        """
        available_extensions = list(self.extensions.keys())
        dependency_issues = {}
        
        for name, extension in self.extensions.items():
            missing_deps = extension.validate_dependencies(available_extensions)
            if missing_deps:
                dependency_issues[name] = missing_deps
                
        return dependency_issues
    
    def execute_extension_method(self, extension_name: str, method_name: str, *args, **kwargs) -> Any:
        """Execute a method on an extension.
        
        Args:
            extension_name: Extension name
            method_name: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Method result
            
        Raises:
            ValueError: If extension not found or not enabled
            AttributeError: If method not found
        """
        extension = self.get_extension(extension_name)
        if extension is None:
            raise ValueError(f"Extension {extension_name} not found")
        
        if not extension.enabled:
            raise ValueError(f"Extension {extension_name} is not enabled")
        
        if not hasattr(extension, method_name):
            raise AttributeError(f"Extension {extension_name} does not have method {method_name}")
        
        method = getattr(extension, method_name)
        if not callable(method):
            raise AttributeError(f"Extension {extension_name}.{method_name} is not callable")
        
        logger.info(f"Executing {extension_name}.{method_name}")
        return method(*args, **kwargs)
    
    def cleanup(self) -> None:
        """Clean up all extensions."""
        for extension in self.extensions.values():
            try:
                extension.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up extension {extension.metadata.name}: {e}")


# Example extension implementations
class ExampleAnalysisExtension(AnalysisExtension):
    """Example analysis extension."""
    
    def __init__(self):
        super().__init__(
            name="example_analysis_extension",
            version="1.0.0",
            description="Example analysis extension for demonstration",
            author="Microcosting Team",
            license="MIT"
        )
    
    def analyze(self, data: Any, **kwargs) -> Any:
        """Perform example analysis."""
        logger.info("Performing example analysis")
        # This is just a placeholder - real analysis would go here
        return {
            "analysis_type": "example",
            "data_size": len(str(data)),
            "timestamp": datetime.now().isoformat()
        }


class ExampleVisualizationExtension(VisualizationExtension):
    """Example visualization extension."""
    
    def __init__(self):
        super().__init__(
            name="example_visualization_extension",
            version="1.0.0",
            description="Example visualization extension for demonstration",
            author="Microcosting Team",
            license="MIT"
        )
    
    def visualize(self, data: Any, **kwargs) -> Any:
        """Create example visualization."""
        logger.info("Creating example visualization")
        # This is just a placeholder - real visualization would go here
        return {
            "visualization_type": "example",
            "data_size": len(str(data)),
            "timestamp": datetime.now().isoformat()
        }


# Example usage function
def example_usage():
    """Example of how to use the extensibility framework."""
    print("Extensibility Framework Example")
    
    # Create data manager
    data_manager = DataManager()
    
    # Create extensibility framework
    framework = ExtensibilityFramework()
    framework.set_data_manager(data_manager)
    
    # Register example extensions
    analysis_extension = ExampleAnalysisExtension()
    viz_extension = ExampleVisualizationExtension()
    
    framework.register_extension(analysis_extension)
    framework.register_extension(viz_extension)
    
    # List extensions
    extensions = framework.list_extensions()
    print(f"Registered extensions: {len(extensions)}")
    for extension in extensions:
        print(f"  - {extension['name']} v{extension['version']}: {extension['description']}")
    
    # Execute extension methods
    try:
        result = framework.execute_extension_method("example_analysis_extension", "analyze", "test data")
        print(f"Analysis result: {result}")
        
        viz_result = framework.execute_extension_method("example_visualization_extension", "visualize", "test data")
        print(f"Visualization result: {viz_result}")
    except Exception as e:
        print(f"Error executing extension method: {e}")
    
    # Cleanup
    framework.cleanup()


if __name__ == "__main__":
    example_usage()