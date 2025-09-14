"""Tests for the plugin system."""

import pytest
from pathlib import Path
import tempfile

from genomics_microcosting.plugin_system import (
    Plugin, AnalysisPlugin, VisualizationPlugin, PluginManager
)


class TestPlugin(Plugin):
    """Test plugin implementation."""
    
    def __init__(self):
        super().__init__(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin for testing"
        )
        self.initialized = False
        self.cleaned_up = False
    
    def initialize(self) -> None:
        """Initialize the plugin."""
        self.initialized = True
    
    def cleanup(self) -> None:
        """Clean up the plugin."""
        self.cleaned_up = True


class TestAnalysisPlugin(AnalysisPlugin):
    """Test analysis plugin."""
    
    def __init__(self):
        super().__init__(
            name="test_analysis",
            version="1.0.0",
            description="Test analysis plugin"
        )
    
    def analyze(self, data):
        """Perform analysis."""
        return f"analyzed: {data}"


class TestVisualizationPlugin(VisualizationPlugin):
    """Test visualization plugin."""
    
    def __init__(self):
        super().__init__(
            name="test_visualization",
            version="1.0.0",
            description="Test visualization plugin"
        )
    
    def visualize(self, data, **kwargs):
        """Create visualization."""
        return f"visualized: {data}"


def test_plugin_base_class():
    """Test the base Plugin class."""
    plugin = Plugin("test", "1.0.0", "Test plugin")
    
    assert plugin.name == "test"
    assert plugin.version == "1.0.0"
    assert plugin.description == "Test plugin"
    assert plugin.enabled is True
    
    # Test default initialize and cleanup methods
    plugin.initialize()  # Should not raise
    plugin.cleanup()     # Should not raise


def test_analysis_plugin():
    """Test the AnalysisPlugin class."""
    plugin = TestAnalysisPlugin()
    
    assert plugin.name == "test_analysis"
    assert plugin.version == "1.0.0"
    assert plugin.description == "Test analysis plugin"
    
    # Test analyze method
    result = plugin.analyze("test_data")
    assert result == "analyzed: test_data"


def test_visualization_plugin():
    """Test the VisualizationPlugin class."""
    plugin = TestVisualizationPlugin()
    
    assert plugin.name == "test_visualization"
    assert plugin.version == "1.0.0"
    assert plugin.description == "Test visualization plugin"
    
    # Test visualize method
    result = plugin.visualize("test_data", param="value")
    assert result == "visualized: test_data"


def test_plugin_manager_initialization():
    """Test PluginManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        
        assert plugin_manager.plugin_directory == plugin_dir
        assert len(plugin_manager.plugins) == 0


def test_plugin_manager_register_plugin():
    """Test registering plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        plugin = TestPlugin()
        
        plugin_manager.register_plugin(plugin)
        
        assert len(plugin_manager.plugins) == 1
        assert "test_plugin" in plugin_manager.plugins
        assert plugin_manager.plugins["test_plugin"] == plugin


def test_plugin_manager_get_plugin():
    """Test getting plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        plugin = TestPlugin()
        plugin_manager.register_plugin(plugin)
        
        # Test getting existing plugin
        retrieved_plugin = plugin_manager.get_plugin("test_plugin")
        assert retrieved_plugin == plugin
        
        # Test getting non-existent plugin
        retrieved_plugin = plugin_manager.get_plugin("nonexistent")
        assert retrieved_plugin is None


def test_plugin_manager_list_plugins():
    """Test listing plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        
        # Register multiple plugins
        plugin1 = TestPlugin()
        plugin2 = TestAnalysisPlugin()
        plugin3 = TestVisualizationPlugin()
        
        plugin_manager.register_plugin(plugin1)
        plugin_manager.register_plugin(plugin2)
        plugin_manager.register_plugin(plugin3)
        
        # List plugins
        plugins = plugin_manager.list_plugins()
        assert len(plugins) == 3
        
        # Check plugin information
        plugin_names = [p["name"] for p in plugins]
        assert "test_plugin" in plugin_names
        assert "test_analysis" in plugin_names
        assert "test_visualization" in plugin_names


def test_plugin_manager_enable_disable():
    """Test enabling and disabling plugins."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        plugin = TestPlugin()
        plugin_manager.register_plugin(plugin)
        
        # Plugin should be enabled by default
        assert plugin.enabled is True
        
        # Disable plugin
        result = plugin_manager.disable_plugin("test_plugin")
        assert result is True
        assert plugin.enabled is False
        
        # Enable plugin
        result = plugin_manager.enable_plugin("test_plugin")
        assert result is True
        assert plugin.enabled is True
        
        # Try to enable/disable non-existent plugin
        result = plugin_manager.enable_plugin("nonexistent")
        assert result is False
        
        result = plugin_manager.disable_plugin("nonexistent")
        assert result is False


def test_plugin_manager_execute_plugin_method():
    """Test executing plugin methods."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        
        # Register plugins
        analysis_plugin = TestAnalysisPlugin()
        viz_plugin = TestVisualizationPlugin()
        plugin_manager.register_plugin(analysis_plugin)
        plugin_manager.register_plugin(viz_plugin)
        
        # Execute analyze method
        result = plugin_manager.execute_plugin_method("test_analysis", "analyze", "test_data")
        assert result == "analyzed: test_data"
        
        # Execute visualize method
        result = plugin_manager.execute_plugin_method("test_visualization", "visualize", "test_data")
        assert result == "visualized: test_data"
        
        # Try to execute method on non-existent plugin
        with pytest.raises(ValueError, match="Plugin nonexistent not found"):
            plugin_manager.execute_plugin_method("nonexistent", "analyze", "test_data")
        
        # Try to execute non-existent method
        with pytest.raises(AttributeError, match="Plugin test_analysis does not have method nonexistent_method"):
            plugin_manager.execute_plugin_method("test_analysis", "nonexistent_method", "test_data")
        
        # Try to execute non-existent method
        with pytest.raises(AttributeError, match="Plugin test_analysis does not have method nonexistent_method"):
            plugin_manager.execute_plugin_method("test_analysis", "nonexistent_method", "test_data")


def test_plugin_manager_plugin_cleanup():
    """Test plugin cleanup."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()
        
        plugin_manager = PluginManager(plugin_dir)
        plugin = TestPlugin()
        plugin_manager.register_plugin(plugin)
        
        # Initialize plugin
        plugin.initialize()
        assert plugin.initialized is True
        
        # Cleanup plugins
        plugin_manager.cleanup()
        assert plugin.cleaned_up is True


if __name__ == "__main__":
    pytest.main([__file__])