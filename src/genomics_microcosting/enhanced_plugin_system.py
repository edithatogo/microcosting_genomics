"""Enhanced plugin system with more sophisticated plugin management."""

import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
import json
from dataclasses import dataclass, asdict
from datetime import datetime

from .logging_config import get_logger
from .plugin_system import Plugin, AnalysisPlugin, VisualizationPlugin


logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    license: str
    dependencies: List[str]
    tags: List[str]
    created_date: str
    last_updated: str


class EnhancedPlugin(Plugin):
    """Enhanced plugin with metadata and lifecycle management."""
    
    def __init__(self, name: str, version: str, description: str, 
                 author: str = "", license: str = "", dependencies: List[str] = None,
                 tags: List[str] = None):
        """Initialize an enhanced plugin.
        
        Args:
            name (str): Plugin name
            version (str): Plugin version
            description (str): Plugin description
            author (str): Plugin author
            license (str): Plugin license
            dependencies (List[str]): Plugin dependencies
            tags (List[str]): Plugin tags for categorization
        """
        super().__init__(name, version, description)
        self.metadata = PluginMetadata(
            name=name,
            version=version,
            description=description,
            author=author,
            license=license,
            dependencies=dependencies or [],
            tags=tags or [],
            created_date=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        self.initialized = False
        self.config: Dict[str, Any] = {}
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set plugin configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
        """
        self.config = config
        self.metadata.last_updated = datetime.now().isoformat()
    
    def get_config(self) -> Dict[str, Any]:
        """Get plugin configuration.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        return self.config
    
    def export_metadata(self) -> Dict[str, Any]:
        """Export plugin metadata.
        
        Returns:
            Dict[str, Any]: Plugin metadata as dictionary
        """
        return asdict(self.metadata)
    
    def validate_dependencies(self, available_plugins: List[str]) -> List[str]:
        """Validate plugin dependencies.
        
        Args:
            available_plugins (List[str]): List of available plugin names
            
        Returns:
            List[str]: List of missing dependencies
        """
        missing_deps = []
        for dep in self.metadata.dependencies:
            if dep not in available_plugins:
                missing_deps.append(dep)
        return missing_deps


class DataProcessingPlugin(EnhancedPlugin):
    """Plugin for data processing functionality."""
    
    def process(self, data: Any, **kwargs) -> Any:
        """Process data.
        
        Args:
            data (Any): Input data
            **kwargs: Additional processing parameters
            
        Returns:
            Any: Processed data
        """
        raise NotImplementedError("Subclasses must implement process method")


class ReportPlugin(EnhancedPlugin):
    """Plugin for report generation functionality."""
    
    def generate_report(self, data: Any, output_format: str = "markdown", **kwargs) -> str:
        """Generate report.
        
        Args:
            data (Any): Input data
            output_format (str): Output format (markdown, html, pdf, etc.)
            **kwargs: Additional report parameters
            
        Returns:
            str: Generated report
        """
        raise NotImplementedError("Subclasses must implement generate_report method")


class EnhancedPluginManager:
    """Enhanced plugin manager with advanced features."""
    
    def __init__(self, plugin_directory: Optional[Path] = None, 
                 config_file: Optional[Path] = None):
        """Initialize the enhanced plugin manager.
        
        Args:
            plugin_directory (Path, optional): Directory to search for plugins
            config_file (Path, optional): Configuration file for plugin settings
        """
        self.plugins: Dict[str, EnhancedPlugin] = {}
        self.plugin_directory = plugin_directory or Path(__file__).resolve().parent / "plugins"
        self.plugin_directory.mkdir(exist_ok=True)
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        
        # Load configuration if provided
        if self.config_file and self.config_file.exists():
            self.load_config()
        
        logger.info(f"EnhancedPluginManager initialized with directory: {self.plugin_directory}")
    
    def load_config(self) -> None:
        """Load plugin manager configuration."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def save_config(self) -> None:
        """Save plugin manager configuration."""
        if self.config_file:
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=2)
                logger.info(f"Saved configuration to {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to save configuration: {e}")
    
    def load_plugin(self, plugin_path: Path) -> EnhancedPlugin:
        """Load an enhanced plugin from a file.
        
        Args:
            plugin_path (Path): Path to the plugin file
            
        Returns:
            EnhancedPlugin: Loaded plugin instance
            
        Raises:
            ImportError: If plugin cannot be loaded
        """
        logger.info(f"Loading enhanced plugin from {plugin_path}")
        
        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {plugin_path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the plugin class (should be the only class that inherits from EnhancedPlugin)
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, EnhancedPlugin) and 
                attr != EnhancedPlugin and 
                attr != AnalysisPlugin and 
                attr != VisualizationPlugin and
                attr != DataProcessingPlugin and
                attr != ReportPlugin):
                plugin_class = attr
                break
        
        if plugin_class is None:
            # Try to find a regular Plugin class and convert it
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr != Plugin):
                    # Convert regular plugin to enhanced plugin
                    plugin_class = self._convert_to_enhanced_plugin(attr)
                    break
        
        if plugin_class is None:
            raise ImportError(f"No valid plugin class found in {plugin_path}")
        
        # Create plugin instance
        try:
            plugin_instance = plugin_class()
        except Exception as e:
            raise ImportError(f"Failed to instantiate plugin from {plugin_path}: {e}")
        
        logger.info(f"Loaded enhanced plugin: {plugin_instance.metadata.name} v{plugin_instance.metadata.version}")
        return plugin_instance
    
    def _convert_to_enhanced_plugin(self, plugin_class: Type[Plugin]) -> Type[EnhancedPlugin]:
        """Convert a regular plugin class to an enhanced plugin class.
        
        Args:
            plugin_class (Type[Plugin]): Regular plugin class
            
        Returns:
            Type[EnhancedPlugin]: Enhanced plugin class
        """
        class ConvertedPlugin(EnhancedPlugin):
            def __init__(self):
                # Try to initialize with existing parameters or use defaults
                try:
                    # Create a temporary instance to get attributes
                    temp_instance = plugin_class()
                    super().__init__(
                        name=getattr(temp_instance, 'name', plugin_class.__name__),
                        version=getattr(temp_instance, 'version', '1.0.0'),
                        description=getattr(temp_instance, 'description', 'Converted plugin')
                    )
                except (AttributeError, TypeError, ValueError):
                    super().__init__(
                        name=plugin_class.__name__,
                        version="1.0.0",
                        description="Converted plugin"
                    )
                
                # Copy methods from the original plugin
                for attr_name in dir(plugin_class):
                    if not attr_name.startswith('_'):
                        attr = getattr(plugin_class, attr_name)
                        if callable(attr):
                            setattr(self, attr_name, attr)
        
        ConvertedPlugin.__name__ = plugin_class.__name__
        return ConvertedPlugin
    
    def discover_plugins(self) -> List[Path]:
        """Discover plugin files in the plugin directory.
        
        Returns:
            List[Path]: List of plugin file paths
        """
        plugin_files = []
        for file_path in self.plugin_directory.glob("*.py"):
            if file_path.name != "__init__.py":
                plugin_files.append(file_path)
        
        logger.info(f"Discovered {len(plugin_files)} plugin files")
        return plugin_files
    
    def register_plugin(self, plugin: EnhancedPlugin) -> bool:
        """Register a plugin.
        
        Args:
            plugin (EnhancedPlugin): Plugin instance to register
            
        Returns:
            bool: True if successful, False if plugin has missing dependencies
        """
        # Check dependencies
        available_plugins = list(self.plugins.keys())
        missing_deps = plugin.validate_dependencies(available_plugins)
        if missing_deps:
            logger.warning(f"Plugin {plugin.metadata.name} has missing dependencies: {missing_deps}")
            return False
        
        if plugin.metadata.name in self.plugins:
            logger.warning(f"Plugin {plugin.metadata.name} already registered, replacing")
        
        self.plugins[plugin.metadata.name] = plugin
        logger.info(f"Registered plugin: {plugin.metadata.name}")
        return True
    
    def load_all_plugins(self) -> Dict[str, List[str]]:
        """Load and register all plugins in the plugin directory.
        
        Returns:
            Dict[str, List[str]]: Dictionary with 'loaded' and 'failed' plugin names
        """
        plugin_files = self.discover_plugins()
        loaded_plugins = []
        failed_plugins = []
        
        for plugin_file in plugin_files:
            try:
                plugin = self.load_plugin(plugin_file)
                if self.register_plugin(plugin):
                    loaded_plugins.append(plugin.metadata.name)
                    if plugin.enabled:
                        plugin.initialize()
                        plugin.initialized = True
                else:
                    failed_plugins.append(plugin.metadata.name)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
                failed_plugins.append(plugin_file.name)
        
        return {"loaded": loaded_plugins, "failed": failed_plugins}
    
    def get_plugin(self, name: str) -> Optional[EnhancedPlugin]:
        """Get a registered plugin by name.
        
        Args:
            name (str): Plugin name
            
        Returns:
            EnhancedPlugin: Plugin instance or None if not found
        """
        return self.plugins.get(name)
    
    def list_plugins(self, filter_tags: List[str] = None) -> List[Dict[str, Any]]:
        """List all registered plugins with filtering support.
        
        Args:
            filter_tags (List[str], optional): Filter plugins by tags
            
        Returns:
            List[Dict[str, Any]]: List of plugin information
        """
        plugin_info = []
        for name, plugin in self.plugins.items():
            # Apply tag filtering
            if filter_tags:
                plugin_tags = plugin.metadata.tags
                if not any(tag in plugin_tags for tag in filter_tags):
                    continue
            
            info = plugin.export_metadata()
            info["enabled"] = plugin.enabled
            info["initialized"] = plugin.initialized
            info["type"] = plugin.__class__.__name__
            plugin_info.append(info)
        return plugin_info
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin.
        
        Args:
            name (str): Plugin name
            
        Returns:
            bool: True if successful, False if plugin not found
        """
        plugin = self.get_plugin(name)
        if plugin is None:
            return False
        
        plugin.enabled = True
        logger.info(f"Enabled plugin: {name}")
        return True
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin.
        
        Args:
            name (str): Plugin name
            
        Returns:
            bool: True if successful, False if plugin not found
        """
        plugin = self.get_plugin(name)
        if plugin is None:
            return False
        
        plugin.enabled = False
        logger.info(f"Disabled plugin: {name}")
        return True
    
    def execute_plugin_method(self, plugin_name: str, method_name: str, *args, **kwargs) -> Any:
        """Execute a method on a plugin.
        
        Args:
            plugin_name (str): Plugin name
            method_name (str): Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Any: Method result
            
        Raises:
            ValueError: If plugin not found or not enabled
            AttributeError: If method not found
        """
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            raise ValueError(f"Plugin {plugin_name} not found")
        
        if not plugin.enabled:
            raise ValueError(f"Plugin {plugin_name} is not enabled")
        
        if not hasattr(plugin, method_name):
            raise AttributeError(f"Plugin {plugin_name} does not have method {method_name}")
        
        method = getattr(plugin, method_name)
        if not callable(method):
            raise AttributeError(f"Plugin {plugin_name}.{method_name} is not callable")
        
        logger.info(f"Executing {plugin_name}.{method_name}")
        return method(*args, **kwargs)
    
    def execute_plugins_by_tag(self, tag: str, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute a method on all plugins with a specific tag.
        
        Args:
            tag (str): Tag to filter plugins
            method_name (str): Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Dict[str, Any]: Dictionary of plugin names and their results
        """
        results = {}
        tagged_plugins = [name for name, plugin in self.plugins.items() 
                         if tag in plugin.metadata.tags and plugin.enabled]
        
        for plugin_name in tagged_plugins:
            try:
                result = self.execute_plugin_method(plugin_name, method_name, *args, **kwargs)
                results[plugin_name] = result
            except Exception as e:
                logger.error(f"Error executing {method_name} on plugin {plugin_name}: {e}")
                results[plugin_name] = {"error": str(e)}
        
        return results
    
    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded plugins.
        
        Returns:
            Dict[str, Any]: Plugin statistics
        """
        stats = {
            "total_plugins": len(self.plugins),
            "enabled_plugins": len([p for p in self.plugins.values() if p.enabled]),
            "initialized_plugins": len([p for p in self.plugins.values() if p.initialized]),
            "plugin_types": {},
            "tags": {}
        }
        
        # Count plugin types
        for plugin in self.plugins.values():
            plugin_type = plugin.__class__.__name__
            stats["plugin_types"][plugin_type] = stats["plugin_types"].get(plugin_type, 0) + 1
            
            # Count tags
            for tag in plugin.metadata.tags:
                stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
        
        return stats
    
    def cleanup(self) -> None:
        """Clean up all plugins."""
        for plugin in self.plugins.values():
            try:
                if plugin.initialized:
                    plugin.cleanup()
                    plugin.initialized = False
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin.metadata.name}: {e}")


# Example enhanced plugin implementations
class EnhancedAnalysisPlugin(AnalysisPlugin):
    """Enhanced analysis plugin with configuration support."""
    
    def __init__(self):
        super().__init__(
            name="enhanced_analysis",
            version="1.0.0",
            description="Enhanced analysis plugin with configuration support",
            author="Microcosting Team",
            license="MIT",
            tags=["analysis", "statistics"]
        )
    
    def analyze(self, data: Any, detailed: bool = False) -> Any:
        """Perform enhanced analysis on data.
        
        Args:
            data (Any): Input data
            detailed (bool): Whether to perform detailed analysis
            
        Returns:
            Any: Analysis results
        """
        logger.info(f"Performing enhanced analysis (detailed: {detailed})")
        
        # This is just a placeholder - real analysis would go here
        base_result = {"analysis_type": "enhanced", "data_size": len(str(data))}
        
        if detailed:
            base_result["detailed_stats"] = {
                "character_count": len(str(data)),
                "word_count": len(str(data).split()),
                "line_count": len(str(data).splitlines())
            }
        
        return base_result


class EnhancedVisualizationPlugin(VisualizationPlugin):
    """Enhanced visualization plugin with multiple output formats."""
    
    def __init__(self):
        super().__init__(
            name="enhanced_visualization",
            version="1.0.0",
            description="Enhanced visualization plugin with multiple output formats",
            author="Microcosting Team",
            license="MIT",
            tags=["visualization", "plotting"]
        )
    
    def visualize(self, data: Any, output_format: str = "png", **kwargs) -> Any:
        """Create enhanced visualization of data.
        
        Args:
            data (Any): Input data
            output_format (str): Output format (png, svg, html, etc.)
            **kwargs: Additional visualization parameters
            
        Returns:
            Any: Visualization object
        """
        logger.info(f"Creating enhanced visualization in {output_format} format")
        
        # This is just a placeholder - real visualization would go here
        return {
            "visualization_type": "enhanced", 
            "data_size": len(str(data)),
            "format": output_format,
            "parameters": kwargs
        }


# Example usage function
def example_usage():
    """Example of how to use the enhanced plugin system."""
    print("Enhanced Plugin System Example")
    
    # Create enhanced plugin manager
    plugin_manager = EnhancedPluginManager()
    
    # Register example plugins
    analysis_plugin = EnhancedAnalysisPlugin()
    viz_plugin = EnhancedVisualizationPlugin()
    
    plugin_manager.register_plugin(analysis_plugin)
    plugin_manager.register_plugin(viz_plugin)
    
    # List plugins
    plugins = plugin_manager.list_plugins()
    print(f"Registered plugins: {len(plugins)}")
    for plugin in plugins:
        print(f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}")
        print(f"    Tags: {plugin['tags']}")
        print(f"    Author: {plugin['author']}")
        print(f"    License: {plugin['license']}")
    
    # Execute plugin methods
    try:
        result = plugin_manager.execute_plugin_method("enhanced_analysis", "analyze", "test data", detailed=True)
        print(f"Analysis result: {result}")
        
        viz_result = plugin_manager.execute_plugin_method("enhanced_visualization", "visualize", "test data", output_format="html")
        print(f"Visualization result: {viz_result}")
    except Exception as e:
        print(f"Error executing plugin method: {e}")
    
    # Get statistics
    stats = plugin_manager.get_plugin_statistics()
    print(f"Plugin statistics: {stats}")
    
    # Cleanup
    plugin_manager.cleanup()


if __name__ == "__main__":
    example_usage()