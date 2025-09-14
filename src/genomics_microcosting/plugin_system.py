"""Plugin system for extending microcosting functionality."""

import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional
from .logging_config import get_logger


logger = get_logger(__name__)


class Plugin:
    """Base class for all plugins."""
    
    def __init__(self, name: str, version: str, description: str):
        """Initialize a plugin.
        
        Args:
            name (str): Plugin name
            version (str): Plugin version
            description (str): Plugin description
        """
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        pass
    
    def cleanup(self) -> None:
        """Clean up the plugin."""
        pass


class AnalysisPlugin(Plugin):
    """Plugin for analysis functionality."""
    
    def analyze(self, data: Any) -> Any:
        """Perform analysis on data.
        
        Args:
            data (Any): Input data
            
        Returns:
            Any: Analysis results
        """
        raise NotImplementedError("Subclasses must implement analyze method")


class VisualizationPlugin(Plugin):
    """Plugin for visualization functionality."""
    
    def visualize(self, data: Any, **kwargs) -> Any:
        """Create visualization of data.
        
        Args:
            data (Any): Input data
            **kwargs: Additional visualization parameters
            
        Returns:
            Any: Visualization object
        """
        raise NotImplementedError("Subclasses must implement visualize method")


class PluginManager:
    """Manages loading, registering, and executing plugins."""
    
    def __init__(self, plugin_directory: Optional[Path] = None):
        """Initialize the plugin manager.
        
        Args:
            plugin_directory (Path, optional): Directory to search for plugins
        """
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_directory = plugin_directory or Path(__file__).resolve().parent / "plugins"
        self.plugin_directory.mkdir(exist_ok=True)
        
        logger.info(f"PluginManager initialized with directory: {self.plugin_directory}")
    
    def load_plugin(self, plugin_path: Path) -> Plugin:
        """Load a plugin from a file.
        
        Args:
            plugin_path (Path): Path to the plugin file
            
        Returns:
            Plugin: Loaded plugin instance
            
        Raises:
            ImportError: If plugin cannot be loaded
        """
        logger.info(f"Loading plugin from {plugin_path}")
        
        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {plugin_path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the plugin class (should be the only class that inherits from Plugin)
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Plugin) and 
                attr != Plugin and 
                attr != AnalysisPlugin and 
                attr != VisualizationPlugin):
                plugin_class = attr
                break
        
        if plugin_class is None:
            raise ImportError(f"No valid plugin class found in {plugin_path}")
        
        # Create plugin instance
        try:
            plugin_instance = plugin_class()
        except Exception as e:
            raise ImportError(f"Failed to instantiate plugin from {plugin_path}: {e}")
        
        logger.info(f"Loaded plugin: {plugin_instance.name} v{plugin_instance.version}")
        return plugin_instance
    
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
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.
        
        Args:
            plugin (Plugin): Plugin instance to register
        """
        if plugin.name in self.plugins:
            logger.warning(f"Plugin {plugin.name} already registered, replacing")
        
        self.plugins[plugin.name] = plugin
        logger.info(f"Registered plugin: {plugin.name}")
    
    def load_all_plugins(self) -> None:
        """Load and register all plugins in the plugin directory."""
        plugin_files = self.discover_plugins()
        
        for plugin_file in plugin_files:
            try:
                plugin = self.load_plugin(plugin_file)
                self.register_plugin(plugin)
                if plugin.enabled:
                    plugin.initialize()
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file}: {e}")
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a registered plugin by name.
        
        Args:
            name (str): Plugin name
            
        Returns:
            Plugin: Plugin instance or None if not found
        """
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins.
        
        Returns:
            List[Dict[str, Any]]: List of plugin information
        """
        plugin_info = []
        for name, plugin in self.plugins.items():
            plugin_info.append({
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "enabled": plugin.enabled,
                "type": plugin.__class__.__name__
            })
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
    
    def cleanup(self) -> None:
        """Clean up all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin.name}: {e}")


# Example plugin implementations
class ExampleAnalysisPlugin(AnalysisPlugin):
    """Example analysis plugin."""
    
    def __init__(self):
        super().__init__(
            name="example_analysis",
            version="1.0.0",
            description="Example analysis plugin for demonstration"
        )
    
    def analyze(self, data: Any) -> Any:
        """Perform example analysis."""
        logger.info("Performing example analysis")
        # This is just a placeholder - real analysis would go here
        return {"analysis_type": "example", "data_size": len(str(data))}


class ExampleVisualizationPlugin(VisualizationPlugin):
    """Example visualization plugin."""
    
    def __init__(self):
        super().__init__(
            name="example_visualization",
            version="1.0.0",
            description="Example visualization plugin for demonstration"
        )
    
    def visualize(self, data: Any, **kwargs) -> Any:
        """Create example visualization."""
        logger.info("Creating example visualization")
        # This is just a placeholder - real visualization would go here
        return {"visualization_type": "example", "data_size": len(str(data))}


# Example usage function
def example_usage():
    """Example of how to use the plugin system."""
    print("Plugin System Example")
    
    # Create plugin manager
    plugin_manager = PluginManager()
    
    # Register example plugins
    analysis_plugin = ExampleAnalysisPlugin()
    viz_plugin = ExampleVisualizationPlugin()
    
    plugin_manager.register_plugin(analysis_plugin)
    plugin_manager.register_plugin(viz_plugin)
    
    # List plugins
    plugins = plugin_manager.list_plugins()
    print(f"Registered plugins: {len(plugins)}")
    for plugin in plugins:
        print(f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}")
    
    # Execute plugin methods
    try:
        result = plugin_manager.execute_plugin_method("example_analysis", "analyze", "test data")
        print(f"Analysis result: {result}")
        
        viz_result = plugin_manager.execute_plugin_method("example_visualization", "visualize", "test data")
        print(f"Visualization result: {viz_result}")
    except Exception as e:
        print(f"Error executing plugin method: {e}")
    
    # Cleanup
    plugin_manager.cleanup()


if __name__ == "__main__":
    example_usage()