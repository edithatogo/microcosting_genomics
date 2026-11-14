# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Tests for the plugin system."""

import tempfile
from pathlib import Path

import pytest

from genomics_microcosting.plugin_system import (
    AnalysisPlugin,
    Plugin,
    PluginManager,
    VisualizationPlugin,
)
from tests.checks import require_equal


class ExamplePlugin(Plugin):
    """Test plugin implementation."""

    def __init__(self) -> None:
        """Create a plugin with observable initialization and cleanup."""
        super().__init__(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin for testing",
        )
        self.initialized = False
        self.cleaned_up = False

    def initialize(self) -> None:
        """Initialize the plugin."""
        self.initialized = True

    def cleanup(self) -> None:
        """Clean up the plugin."""
        self.cleaned_up = True


class ExampleAnalysisPlugin(AnalysisPlugin):
    """Test analysis plugin."""

    def __init__(self) -> None:
        """Register the analysis fixture with a stable name."""
        super().__init__(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis plugin",
        )

    def analyze(self, data: object) -> str:
        """Perform analysis."""
        return f"analyzed: {data}"


class ExampleVisualizationPlugin(VisualizationPlugin):
    """Test visualization plugin."""

    def __init__(self) -> None:
        """Register the visualisation fixture with a stable name."""
        super().__init__(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization plugin",
        )

    def visualize(self, data: object, **_kwargs: object) -> str:
        """Create visualization."""
        return f"visualized: {data}"


def test_plugin_base_class() -> None:
    """Test the base Plugin class."""
    plugin = Plugin("test", "1.0.0", "Test plugin")

    if not (plugin.name == "test"):
        raise AssertionError
    if not (plugin.version == "1.0.0"):
        raise AssertionError
    if not (plugin.description == "Test plugin"):
        raise AssertionError
    if plugin.enabled is not True:
        raise AssertionError

    # Test default initialize and cleanup methods
    plugin.initialize()  # Should not raise
    plugin.cleanup()  # Should not raise


def test_analysis_plugin() -> None:
    """Test the AnalysisPlugin class."""
    plugin = ExampleAnalysisPlugin()

    if not (plugin.name == "test_analysis"):
        raise AssertionError
    if not (plugin.version == "1.0.0"):
        raise AssertionError
    if not (plugin.description == "Test analysis plugin"):
        raise AssertionError

    # Test analyze method
    result = plugin.analyze("test_data")
    if not (result == "analyzed: test_data"):
        raise AssertionError


def test_visualization_plugin() -> None:
    """Test the VisualizationPlugin class."""
    plugin = ExampleVisualizationPlugin()

    if not (plugin.name == "test_visualization"):
        raise AssertionError
    if not (plugin.version == "1.0.0"):
        raise AssertionError
    if not (plugin.description == "Test visualization plugin"):
        raise AssertionError

    # Test visualize method
    result = plugin.visualize("test_data", param="value")
    if not (result == "visualized: test_data"):
        raise AssertionError


def test_plugin_manager_initialization() -> None:
    """Test PluginManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)

        if not (plugin_manager.plugin_directory == plugin_dir):
            raise AssertionError
        if not (len(plugin_manager.plugins) == 0):
            raise AssertionError


def test_plugin_manager_register_plugin() -> None:
    """Test registering plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)
        plugin = ExamplePlugin()

        plugin_manager.register_plugin(plugin)

        if not (len(plugin_manager.plugins) == 1):
            raise AssertionError
        if "test_plugin" not in plugin_manager.plugins:
            raise AssertionError
        if not (plugin_manager.plugins["test_plugin"] == plugin):
            raise AssertionError


def test_plugin_manager_get_plugin() -> None:
    """Test getting plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)
        plugin = ExamplePlugin()
        plugin_manager.register_plugin(plugin)

        # Test getting existing plugin
        retrieved_plugin = plugin_manager.get_plugin("test_plugin")
        if not (retrieved_plugin == plugin):
            raise AssertionError

        # Test getting non-existent plugin
        retrieved_plugin = plugin_manager.get_plugin("nonexistent")
        if retrieved_plugin is not None:
            raise AssertionError


def test_plugin_manager_list_plugins() -> None:
    """Test listing plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)

        # Register multiple plugins
        plugin1 = ExamplePlugin()
        plugin2 = ExampleAnalysisPlugin()
        plugin3 = ExampleVisualizationPlugin()

        plugin_manager.register_plugin(plugin1)
        plugin_manager.register_plugin(plugin2)
        plugin_manager.register_plugin(plugin3)

        # List plugins
        plugins = plugin_manager.list_plugins()
        require_equal(len(plugins), 3)

        # Check plugin information
        plugin_names = [p["name"] for p in plugins]
        if "test_plugin" not in plugin_names:
            raise AssertionError
        if "test_analysis" not in plugin_names:
            raise AssertionError
        if "test_visualization" not in plugin_names:
            raise AssertionError


def test_plugin_manager_enable_disable() -> None:
    """Test enabling and disabling plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)
        plugin = ExamplePlugin()
        plugin_manager.register_plugin(plugin)

        # Plugin should be enabled by default
        if plugin.enabled is not True:
            raise AssertionError

        # Disable plugin
        result = plugin_manager.disable_plugin("test_plugin")
        if result is not True:
            raise AssertionError
        disabled = False
        require_equal(plugin.enabled, disabled)

        # Enable plugin
        result = plugin_manager.enable_plugin("test_plugin")
        if result is not True:
            raise AssertionError
        if plugin.enabled is not True:
            raise AssertionError

        # Try to enable/disable non-existent plugin
        result = plugin_manager.enable_plugin("nonexistent")
        if result is not False:
            raise AssertionError

        result = plugin_manager.disable_plugin("nonexistent")
        if result is not False:
            raise AssertionError


def test_plugin_manager_execute_plugin_method() -> None:
    """Test executing plugin methods."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)

        # Register plugins
        analysis_plugin = ExampleAnalysisPlugin()
        viz_plugin = ExampleVisualizationPlugin()
        plugin_manager.register_plugin(analysis_plugin)
        plugin_manager.register_plugin(viz_plugin)

        # Execute analyze method
        result = plugin_manager.execute_plugin_method(
            "test_analysis",
            "analyze",
            "test_data",
        )
        if not (result == "analyzed: test_data"):
            raise AssertionError

        # Execute visualize method
        result = plugin_manager.execute_plugin_method(
            "test_visualization",
            "visualize",
            "test_data",
        )
        if not (result == "visualized: test_data"):
            raise AssertionError

        # Try to execute method on non-existent plugin
        with pytest.raises(ValueError, match="Plugin nonexistent not found"):
            plugin_manager.execute_plugin_method("nonexistent", "analyze", "test_data")

        # Try to execute an attribute that exists but cannot be called
        with pytest.raises(
            AttributeError,
            match=r"Plugin test_analysis\.enabled is not callable",
        ):
            plugin_manager.execute_plugin_method(
                "test_analysis",
                "enabled",
                "test_data",
            )

        # Try to execute non-existent method
        with pytest.raises(
            AttributeError,
            match="Plugin test_analysis does not have method nonexistent_method",
        ):
            plugin_manager.execute_plugin_method(
                "test_analysis",
                "nonexistent_method",
                "test_data",
            )


def test_plugin_manager_plugin_cleanup() -> None:
    """Test plugin cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        plugin_manager = PluginManager(plugin_dir)
        plugin = ExamplePlugin()
        plugin_manager.register_plugin(plugin)

        # Initialize plugin
        plugin.initialize()
        if plugin.initialized is not True:
            raise AssertionError

        # Cleanup plugins
        plugin_manager.cleanup()
        if plugin.cleaned_up is not True:
            raise AssertionError


if __name__ == "__main__":
    pytest.main([__file__])
