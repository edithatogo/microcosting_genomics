# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Plugin system for extending microcosting functionality."""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any, cast
lazy from collections.abc import Callable

from .logging_config import get_logger

logger = get_logger(__name__)

_MISSING_METHOD = object()


def get_plugin_method(
    plugin: object,
    name: str,
    label: str,
    method_name: str,
) -> Callable[..., object]:
    """Resolve a callable attribute once and preserve plugin lookup errors."""
    method: object = getattr(plugin, method_name, _MISSING_METHOD)
    if method is _MISSING_METHOD:
        message = f"{label} {name} does not have method {method_name}"
    elif callable(method):
        return method
    else:
        message = f"{label} {name}.{method_name} is not callable"
    raise AttributeError(message)


class Plugin:
    """Base class for all plugins."""

    def __init__(self, name: str, version: str, description: str) -> None:
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

    def cleanup(self) -> None:
        """Clean up the plugin."""


class AnalysisPlugin(Plugin):
    """Plugin for analysis functionality."""

    def analyze(self, data: object) -> object:
        """Perform analysis on data.

        Args:
            data (object): Input data

        Returns:
            Any: Analysis results

        """
        message = "Subclasses must implement analyze method"
        raise NotImplementedError(message)


class VisualizationPlugin(Plugin):
    """Plugin for visualization functionality."""

    def visualize(self, data: object, **kwargs: object) -> object:
        """Create visualization of data.

        Args:
            data (object): Input data
            **kwargs: Additional visualization parameters

        Returns:
            Any: Visualization object

        """
        message = "Subclasses must implement visualize method"
        raise NotImplementedError(message)


class PluginManager:
    """Manages loading, registering, and executing plugins."""

    def __init__(self, plugin_directory: Path | None = None) -> None:
        """Initialize the plugin manager.

        Args:
            plugin_directory (Path, optional): Directory to search for plugins

        """
        self.plugins: dict[str, Plugin] = {}
        self.plugin_directory = (
            plugin_directory or Path(__file__).resolve().parent / "plugins"
        )
        self.plugin_directory.mkdir(exist_ok=True)

        logger.info(
            "PluginManager initialized with directory: %s",
            self.plugin_directory,
        )

    def load_plugin(self, plugin_path: Path) -> Plugin:
        """Load a plugin from a file.

        Args:
            plugin_path (Path): Path to the plugin file

        Returns:
            Plugin: Loaded plugin instance

        Raises:
            ImportError: If plugin cannot be loaded

        """
        logger.info("Loading plugin from %s", plugin_path)

        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
        if spec is None or spec.loader is None:
            message = f"Cannot load plugin from {plugin_path}"
            raise ImportError(message)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the plugin class (should be the only class that inherits from Plugin)
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Plugin)
                and attr
                not in (
                    Plugin,
                    AnalysisPlugin,
                    VisualizationPlugin,
                )
            ):
                plugin_class = attr
                break

        if plugin_class is None:
            message = f"No valid plugin class found in {plugin_path}"
            raise ImportError(message)

        # Create plugin instance
        try:
            plugin_instance = cast("Callable[[], Plugin]", plugin_class)()
        except Exception as e:
            message = f"Failed to instantiate plugin from {plugin_path}: {e}"
            raise ImportError(message) from e

        logger.info(
            "Loaded plugin: %s v%s",
            plugin_instance.name,
            plugin_instance.version,
        )
        return plugin_instance

    def discover_plugins(self) -> list[Path]:
        """Discover plugin files in the plugin directory.

        Returns:
            List[Path]: List of plugin file paths

        """
        plugin_files = [
            file_path
            for file_path in self.plugin_directory.glob("*.py")
            if file_path.name != "__init__.py"
        ]

        logger.info("Discovered %s plugin files", len(plugin_files))
        return plugin_files

    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin.

        Args:
            plugin (Plugin): Plugin instance to register

        """
        if plugin.name in self.plugins:
            logger.warning("Plugin %s already registered, replacing", plugin.name)

        self.plugins[plugin.name] = plugin
        logger.info("Registered plugin: %s", plugin.name)

    def load_all_plugins(self) -> None:
        """Load and register all plugins in the plugin directory."""
        plugin_files = self.discover_plugins()

        for plugin_file in plugin_files:
            try:
                plugin = self.load_plugin(plugin_file)
                self.register_plugin(plugin)
                if plugin.enabled:
                    plugin.initialize()
            except Exception:
                logger.exception("Failed to load plugin %s", plugin_file)

    def get_plugin(self, name: str) -> Plugin | None:
        """Get a registered plugin by name.

        Args:
            name (str): Plugin name

        Returns:
            Plugin: Plugin instance or None if not found

        """
        return self.plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins.

        Returns:
            List[Dict[str, Any]]: List of plugin information

        """
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "enabled": plugin.enabled,
                "type": plugin.__class__.__name__,
            }
            for plugin in self.plugins.values()
        ]

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
        logger.info("Enabled plugin: %s", name)
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
        logger.info("Disabled plugin: %s", name)
        return True

    def execute_plugin_method(
        self,
        plugin_name: str,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> object:
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
            AttributeError: If the method is missing or is not callable

        """
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            message = f"Plugin {plugin_name} not found"
            raise ValueError(message)

        if not plugin.enabled:
            message = f"Plugin {plugin_name} is not enabled"
            raise ValueError(message)

        method = get_plugin_method(plugin, plugin_name, "Plugin", method_name)

        logger.info("Executing %s.%s", plugin_name, method_name)
        return method(*args, **kwargs)

    def cleanup(self) -> None:
        """Clean up all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception:
                logger.exception("Error cleaning up plugin %s", plugin.name)


# Example plugin implementations
class ExampleAnalysisPlugin(AnalysisPlugin):
    """Example analysis plugin."""

    def __init__(self) -> None:
        """Register metadata for the example analysis plugin."""
        super().__init__(
            name="example_analysis",
            version="1.0.0",
            description="Example analysis plugin for demonstration",
        )

    def analyze(self, data: object) -> object:
        """Perform example analysis."""
        logger.info("Performing example analysis")
        # This is just a placeholder - real analysis would go here
        return {"analysis_type": "example", "data_size": len(str(data))}


class ExampleVisualizationPlugin(VisualizationPlugin):
    """Example visualization plugin."""

    def __init__(self) -> None:
        """Register metadata for the example visualisation plugin."""
        super().__init__(
            name="example_visualization",
            version="1.0.0",
            description="Example visualization plugin for demonstration",
        )

    def visualize(self, data: object, **_kwargs: object) -> object:
        """Create example visualization."""
        logger.info("Creating example visualization")
        # This is just a placeholder - real visualization would go here
        return {"visualization_type": "example", "data_size": len(str(data))}


# Example usage function
def example_usage() -> None:
    """Demonstrate the plugin system."""
    logger.info("%s", "Plugin System Example")

    # Create plugin manager
    plugin_manager = PluginManager()

    # Register example plugins
    analysis_plugin = ExampleAnalysisPlugin()
    viz_plugin = ExampleVisualizationPlugin()

    plugin_manager.register_plugin(analysis_plugin)
    plugin_manager.register_plugin(viz_plugin)

    # List plugins
    plugins = plugin_manager.list_plugins()
    logger.info("%s", f"Registered plugins: {len(plugins)}")
    for plugin in plugins:
        logger.info(
            "%s",
            f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}",
        )

    # Execute plugin methods
    try:
        result = plugin_manager.execute_plugin_method(
            "example_analysis",
            "analyze",
            "test data",
        )
        logger.info("%s", f"Analysis result: {result}")

        viz_result = plugin_manager.execute_plugin_method(
            "example_visualization",
            "visualize",
            "test data",
        )
        logger.info("%s", f"Visualization result: {viz_result}")
    except AttributeError, RuntimeError, TypeError, ValueError:
        logger.exception("Error executing plugin method")

    # Cleanup
    plugin_manager.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
