# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Enhanced plugin system with more sophisticated plugin management."""

import importlib
import importlib.util
import json
import logging
from dataclasses import InitVar, asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast, override
lazy from collections.abc import Callable

from .logging_config import get_logger
from .plugin_system import (
    AnalysisPlugin,
    Plugin,
    VisualizationPlugin,
    get_plugin_method,
)

logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str
    description: str
    author: str
    license: str
    dependencies: list[str]
    tags: list[str]
    created_date: str
    last_updated: str


@dataclass(eq=False, repr=False, match_args=False)
class EnhancedPlugin(Plugin):
    """Enhanced plugin with metadata and lifecycle management."""

    name: str
    version: str
    description: str
    author: InitVar[str] = ""
    license: InitVar[str] = ""
    dependencies: InitVar[list[str] | None] = None
    tags: InitVar[list[str] | None] = None

    def __post_init__(
        self,
        author: str,
        plugin_license: str,
        dependencies: list[str] | None,
        tags: list[str] | None,
    ) -> None:
        """Initialize lifecycle state and record the supplied metadata."""
        super().__init__(self.name, self.version, self.description)
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=author,
            license=plugin_license,
            dependencies=dependencies or [],
            tags=tags or [],
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
        )
        self.initialized = False
        self.config: dict[str, Any] = {}

    def set_config(self, config: dict[str, Any]) -> None:
        """Set plugin configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary

        """
        self.config = config
        self.metadata.last_updated = datetime.now(UTC).isoformat()

    def get_config(self) -> dict[str, Any]:
        """Get plugin configuration.

        Returns:
            Dict[str, Any]: Configuration dictionary

        """
        return self.config

    def export_metadata(self) -> dict[str, Any]:
        """Export plugin metadata.

        Returns:
            Dict[str, Any]: Plugin metadata as dictionary

        """
        return asdict(self.metadata)

    def validate_dependencies(self, available_plugins: list[str]) -> list[str]:
        """Validate plugin dependencies.

        Args:
            available_plugins (List[str]): List of available plugin names

        Returns:
            List[str]: List of missing dependencies

        """
        return [
            dep for dep in self.metadata.dependencies if dep not in available_plugins
        ]


class DataProcessingPlugin(EnhancedPlugin):
    """Plugin for data processing functionality."""

    def process(self, data: object, **kwargs: object) -> object:
        """Process data.

        Args:
            data (object): Input data
            **kwargs: Additional processing parameters

        Returns:
            Any: Processed data

        """
        message = "Subclasses must implement process method"
        raise NotImplementedError(message)


class ReportPlugin(EnhancedPlugin):
    """Plugin for report generation functionality."""

    def generate_report(
        self,
        data: object,
        output_format: str = "markdown",
        **kwargs: object,
    ) -> str:
        """Generate report.

        Args:
            data (object): Input data
            output_format (str): Output format (markdown, html, pdf, etc.)
            **kwargs: Additional report parameters

        Returns:
            str: Generated report

        """
        message = "Subclasses must implement generate_report method"
        raise NotImplementedError(message)


class PluginStatistics(TypedDict):
    """Counts of loaded plugins, grouped by class and tag."""

    total_plugins: int
    enabled_plugins: int
    initialized_plugins: int
    plugin_types: dict[str, int]
    tags: dict[str, int]


class EnhancedPluginManager:
    """Enhanced plugin manager with advanced features."""

    def __init__(
        self,
        plugin_directory: Path | None = None,
        config_file: Path | None = None,
    ) -> None:
        """Initialize the enhanced plugin manager.

        Args:
            plugin_directory (Path, optional): Directory to search for plugins
            config_file (Path, optional): Configuration file for plugin settings

        """
        self.plugins: dict[str, EnhancedPlugin] = {}
        self.plugin_directory = (
            plugin_directory or Path(__file__).resolve().parent / "plugins"
        )
        self.plugin_directory.mkdir(exist_ok=True)
        self.config_file = config_file
        self.config: dict[str, Any] = {}

        # Load configuration if provided
        if self.config_file and self.config_file.exists():
            self.load_config()

        logger.info(
            "EnhancedPluginManager initialized with directory: %s",
            self.plugin_directory,
        )

    def load_config(self) -> None:
        """Load plugin manager configuration."""
        if self.config_file is None:
            return
        try:
            with self.config_file.open() as f:
                self.config = json.load(f)
            logger.info("Loaded configuration from %s", self.config_file)
        except Exception:
            logger.exception("Failed to load configuration")

    def save_config(self) -> None:
        """Save plugin manager configuration."""
        if self.config_file:
            try:
                with Path(self.config_file).open("w") as f:
                    json.dump(self.config, f, indent=2)
                logger.info("Saved configuration to %s", self.config_file)
            except Exception:
                logger.exception("Failed to save configuration")

    def load_plugin(self, plugin_path: Path) -> EnhancedPlugin:
        """Load an enhanced plugin from a file.

        Args:
            plugin_path (Path): Path to the plugin file

        Returns:
            EnhancedPlugin: Loaded plugin instance

        Raises:
            ImportError: If plugin cannot be loaded

        """
        logger.info("Loading enhanced plugin from %s", plugin_path)

        # Load the module
        spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
        if spec is None or spec.loader is None:
            message = f"Cannot load plugin from {plugin_path}"
            raise ImportError(message)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the plugin class (should be the only class that inherits from
        # EnhancedPlugin)
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, EnhancedPlugin)
                and attr
                not in (
                    EnhancedPlugin,
                    AnalysisPlugin,
                    VisualizationPlugin,
                    DataProcessingPlugin,
                    ReportPlugin,
                )
            ):
                plugin_class = attr
                break

        if plugin_class is None:
            # Try to find a regular Plugin class and convert it
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Plugin)
                    and attr != Plugin
                ):
                    # Convert regular plugin to enhanced plugin
                    plugin_class = self._convert_to_enhanced_plugin(attr)
                    break

        if plugin_class is None:
            message = f"No valid plugin class found in {plugin_path}"
            raise ImportError(message)

        # Create plugin instance
        try:
            plugin_instance = cast("Callable[[], EnhancedPlugin]", plugin_class)()
        except Exception as e:
            message = f"Failed to instantiate plugin from {plugin_path}: {e}"
            raise ImportError(message) from e

        logger.info(
            "Loaded enhanced plugin: %s v%s",
            plugin_instance.metadata.name,
            plugin_instance.metadata.version,
        )
        return plugin_instance

    def _convert_to_enhanced_plugin(
        self,
        plugin_class: type[Plugin],
    ) -> type[EnhancedPlugin]:
        """Convert a regular plugin class to an enhanced plugin class.

        Args:
            plugin_class (Type[Plugin]): Regular plugin class

        Returns:
            Type[EnhancedPlugin]: Enhanced plugin class

        """

        class ConvertedPlugin(EnhancedPlugin):
            def __init__(self) -> None:
                # Try to initialize with existing parameters or use defaults
                try:
                    # Create a temporary instance to get attributes
                    temp_instance = cast("Callable[[], Plugin]", plugin_class)()
                    super().__init__(
                        name=getattr(temp_instance, "name", plugin_class.__name__),
                        version=getattr(temp_instance, "version", "1.0.0"),
                        description=getattr(
                            temp_instance,
                            "description",
                            "Converted plugin",
                        ),
                    )
                except AttributeError, TypeError, ValueError:
                    super().__init__(
                        name=plugin_class.__name__,
                        version="1.0.0",
                        description="Converted plugin",
                    )

                # Copy methods from the original plugin
                for attr_name in dir(plugin_class):
                    if not attr_name.startswith("_"):
                        attr = getattr(plugin_class, attr_name)
                        if callable(attr):
                            setattr(self, attr_name, attr)

        ConvertedPlugin.__name__ = plugin_class.__name__
        return ConvertedPlugin

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
            logger.warning(
                "Plugin %s has missing dependencies: %s",
                plugin.metadata.name,
                missing_deps,
            )
            return False

        if plugin.metadata.name in self.plugins:
            logger.warning(
                "Plugin %s already registered, replacing",
                plugin.metadata.name,
            )

        self.plugins[plugin.metadata.name] = plugin
        logger.info("Registered plugin: %s", plugin.metadata.name)
        return True

    def load_all_plugins(self) -> dict[str, list[str]]:
        """Load and register all plugins in the plugin directory.

        Returns:
            Dict[str, List[str]]: Dictionary with 'loaded' and 'failed' plugin names

        """
        plugin_files = self.discover_plugins()
        loaded_plugins: list[str] = []
        failed_plugins: list[str] = []

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
            except Exception:
                logger.exception("Failed to load plugin %s", plugin_file)
                failed_plugins.append(plugin_file.name)

        return {"loaded": loaded_plugins, "failed": failed_plugins}

    def get_plugin(self, name: str) -> EnhancedPlugin | None:
        """Get a registered plugin by name.

        Args:
            name (str): Plugin name

        Returns:
            EnhancedPlugin: Plugin instance or None if not found

        """
        return self.plugins.get(name)

    def list_plugins(
        self,
        filter_tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List all registered plugins with filtering support.

        Args:
            filter_tags (List[str], optional): Filter plugins by tags

        Returns:
            List[Dict[str, Any]]: List of plugin information

        """
        plugin_info: list[dict[str, Any]] = []
        for plugin in self.plugins.values():
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

    def execute_plugins_by_tag(
        self,
        tag: str,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> dict[str, Any]:
        """Execute a method on all plugins with a specific tag.

        Args:
            tag (str): Tag to filter plugins
            method_name (str): Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Dict[str, Any]: Dictionary of plugin names and their results

        """
        results: dict[str, object] = {}
        tagged_plugins = [
            name
            for name, plugin in self.plugins.items()
            if tag in plugin.metadata.tags and plugin.enabled
        ]

        for plugin_name in tagged_plugins:
            try:
                result = self.execute_plugin_method(
                    plugin_name,
                    method_name,
                    *args,
                    **kwargs,
                )
                results[plugin_name] = result
            except Exception as e:
                logger.exception(
                    "Error executing %s on plugin %s",
                    method_name,
                    plugin_name,
                )
                results[plugin_name] = {"error": str(e)}

        return results

    def get_plugin_statistics(self) -> PluginStatistics:
        """Get statistics about loaded plugins.

        Returns:
            Dict[str, Any]: Plugin statistics

        """
        stats: PluginStatistics = {
            "total_plugins": len(self.plugins),
            "enabled_plugins": len([p for p in self.plugins.values() if p.enabled]),
            "initialized_plugins": len(
                [p for p in self.plugins.values() if p.initialized],
            ),
            "plugin_types": {},
            "tags": {},
        }

        # Count plugin types
        for plugin in self.plugins.values():
            plugin_type = plugin.__class__.__name__
            stats["plugin_types"][plugin_type] = (
                stats["plugin_types"].get(plugin_type, 0) + 1
            )

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
            except Exception:
                logger.exception(
                    "Error cleaning up plugin %s",
                    plugin.metadata.name,
                )


# Example enhanced plugin implementations
class EnhancedAnalysisPlugin(EnhancedPlugin, AnalysisPlugin):
    """Enhanced analysis plugin with configuration support."""

    def __init__(self) -> None:
        """Register metadata for the enhanced analysis example."""
        super().__init__(
            name="enhanced_analysis",
            version="1.0.0",
            description="Enhanced analysis plugin with configuration support",
            author="Microcosting Team",
            license="Apache-2.0",
            tags=["analysis", "statistics"],
        )

    @override
    def analyze(self, data: object, detailed: bool = False) -> dict[str, object]:
        """Perform enhanced analysis on data.

        Args:
            data (object): Input data
            detailed (bool): Whether to perform detailed analysis

        Returns:
            Any: Analysis results

        """
        logger.info("Performing enhanced analysis (detailed: %s)", detailed)

        # This is just a placeholder - real analysis would go here
        base_result: dict[str, object] = {
            "analysis_type": "enhanced",
            "data_size": len(str(data)),
        }

        if detailed:
            base_result["detailed_stats"] = {
                "character_count": len(str(data)),
                "word_count": len(str(data).split()),
                "line_count": len(str(data).splitlines()),
            }

        return base_result


class EnhancedVisualizationPlugin(EnhancedPlugin, VisualizationPlugin):
    """Enhanced visualization plugin with multiple output formats."""

    def __init__(self) -> None:
        """Register metadata for the enhanced visualisation example."""
        super().__init__(
            name="enhanced_visualization",
            version="1.0.0",
            description="Enhanced visualization plugin with multiple output formats",
            author="Microcosting Team",
            license="Apache-2.0",
            tags=["visualization", "plotting"],
        )

    def visualize(
        self,
        data: object,
        output_format: str = "png",
        **kwargs: object,
    ) -> dict[str, object]:
        """Create enhanced visualization of data.

        Args:
            data (object): Input data
            output_format (str): Output format (png, svg, html, etc.)
            **kwargs: Additional visualization parameters

        Returns:
            Any: Visualization object

        """
        logger.info("Creating enhanced visualization in %s format", output_format)

        # This is just a placeholder - real visualization would go here
        return {
            "visualization_type": "enhanced",
            "data_size": len(str(data)),
            "format": output_format,
            "parameters": kwargs,
        }


# Example usage function
def example_usage() -> None:
    """Demonstrate the enhanced plugin system."""
    logger.info("%s", "Enhanced Plugin System Example")

    # Create enhanced plugin manager
    plugin_manager = EnhancedPluginManager()

    # Register example plugins
    analysis_plugin = EnhancedAnalysisPlugin()
    viz_plugin = EnhancedVisualizationPlugin()

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
        logger.info("%s", f"    Tags: {plugin['tags']}")
        logger.info("%s", f"    Author: {plugin['author']}")
        logger.info("%s", f"    License: {plugin['license']}")

    # Execute plugin methods
    try:
        result = plugin_manager.execute_plugin_method(
            "enhanced_analysis",
            "analyze",
            "test data",
            detailed=True,
        )
        logger.info("%s", f"Analysis result: {result}")

        viz_result = plugin_manager.execute_plugin_method(
            "enhanced_visualization",
            "visualize",
            "test data",
            output_format="html",
        )
        logger.info("%s", f"Visualization result: {viz_result}")
    except AttributeError, RuntimeError, TypeError, ValueError:
        logger.exception("Error executing plugin method")

    # Get statistics
    stats = plugin_manager.get_plugin_statistics()
    logger.info("%s", f"Plugin statistics: {stats}")

    # Cleanup
    plugin_manager.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
