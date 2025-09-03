#!/usr/bin/env python3
"""
Script to demonstrate the enhanced plugin system functionality.
"""

import sys
from pathlib import Path
import json
import argparse

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.plugin_system import PluginManager
from unimelb_phd_phase_1.enhanced_plugin_system import EnhancedPluginManager


def demonstrate_basic_plugin_system():
    """Demonstrate the basic plugin system."""
    print("=== Basic Plugin System Demonstration ===")
    
    # Create plugin manager
    plugin_manager = PluginManager()
    
    # Load all plugins
    print("Loading plugins...")
    plugin_manager.load_all_plugins()
    
    # List plugins
    plugins = plugin_manager.list_plugins()
    print(f"\nFound {len(plugins)} plugins:")
    for plugin in plugins:
        print(f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}")
        print(f"    Type: {plugin['type']}")
        print(f"    Enabled: {plugin['enabled']}")
    
    # Execute example plugin methods if available
    for plugin in plugins:
        plugin_name = plugin['name']
        plugin_type = plugin['type']
        
        try:
            if plugin_type == 'ExampleAnalysisPlugin':
                result = plugin_manager.execute_plugin_method(plugin_name, "analyze", "sample data")
                print(f"\nAnalysis result from {plugin_name}: {result}")
            elif plugin_type == 'ExampleVisualizationPlugin':
                result = plugin_manager.execute_plugin_method(plugin_name, "visualize", "sample data")
                print(f"\nVisualization result from {plugin_name}: {result}")
        except Exception as e:
            print(f"\nError executing {plugin_name}: {e}")


def demonstrate_enhanced_plugin_system():
    """Demonstrate the enhanced plugin system."""
    print("\n=== Enhanced Plugin System Demonstration ===")
    
    # Create enhanced plugin manager
    config_file = Path(__file__).resolve().parents[1] / "config" / "plugin_config.json"
    plugin_manager = EnhancedPluginManager(config_file=config_file)
    
    # Load all plugins
    print("Loading enhanced plugins...")
    load_results = plugin_manager.load_all_plugins()
    print(f"Loaded plugins: {load_results['loaded']}")
    if load_results['failed']:
        print(f"Failed to load plugins: {load_results['failed']}")
    
    # List plugins with tag filtering
    print("\nAll plugins:")
    all_plugins = plugin_manager.list_plugins()
    for plugin in all_plugins:
        print(f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}")
        print(f"    Tags: {plugin['tags']}")
        print(f"    Author: {plugin['author']}")
        print(f"    Enabled: {plugin['enabled']}")
        print(f"    Initialized: {plugin['initialized']}")
    
    # List plugins by tag
    print("\nAnalysis plugins:")
    analysis_plugins = plugin_manager.list_plugins(filter_tags=["analysis"])
    for plugin in analysis_plugins:
        print(f"  - {plugin['name']}")
    
    print("\nVisualization plugins:")
    viz_plugins = plugin_manager.list_plugins(filter_tags=["visualization"])
    for plugin in viz_plugins:
        print(f"  - {plugin['name']}")
    
    # Execute plugin methods
    for plugin in all_plugins:
        plugin_name = plugin['name']
        
        try:
            if 'analysis' in plugin['tags']:
                result = plugin_manager.execute_plugin_method(plugin_name, "analyze", "sample data", detailed=True)
                print(f"\nEnhanced analysis result from {plugin_name}: {result}")
            elif 'visualization' in plugin['tags']:
                result = plugin_manager.execute_plugin_method(plugin_name, "visualize", "sample data", output_format="html")
                print(f"\nEnhanced visualization result from {plugin_name}: {result}")
        except Exception as e:
            print(f"\nError executing {plugin_name}: {e}")
    
    # Execute plugins by tag
    print("\nExecuting all analysis plugins:")
    analysis_results = plugin_manager.execute_plugins_by_tag("analysis", "analyze", "test data")
    for plugin_name, result in analysis_results.items():
        print(f"  {plugin_name}: {result}")
    
    # Get plugin statistics
    stats = plugin_manager.get_plugin_statistics()
    print(f"\nPlugin statistics:")
    print(json.dumps(stats, indent=2))
    
    # Export plugin metadata
    print("\nExporting plugin metadata...")
    for plugin in all_plugins:
        plugin_instance = plugin_manager.get_plugin(plugin['name'])
        if plugin_instance:
            metadata = plugin_instance.export_metadata()
            print(f"  {plugin['name']} metadata: {json.dumps(metadata, indent=2)}")


def create_sample_enhanced_plugin():
    """Create a sample enhanced plugin."""
    print("\n=== Creating Sample Enhanced Plugin ===")
    
    plugin_content = '''
"""Sample enhanced cost analysis plugin."""

import pandas as pd
from typing import Any, Dict
from unimelb_phd_phase_1.enhanced_plugin_system import AnalysisPlugin


class SampleCostAnalysisPlugin(AnalysisPlugin):
    """Sample plugin for cost analysis functionality."""
    
    def __init__(self):
        super().__init__(
            name="sample_cost_analysis",
            version="1.0.0",
            description="Sample cost analysis plugin for demonstration",
            author="Microcosting Team",
            license="MIT",
            tags=["analysis", "cost", "finance"]
        )
    
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Perform sample cost analysis.
        
        Args:
            data (Any): Input data
            **kwargs: Additional analysis parameters
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        # Handle different data types
        if isinstance(data, pd.DataFrame):
            result = {
                "data_type": "DataFrame",
                "rows": len(data),
                "columns": len(data.columns),
                "numeric_columns": len(data.select_dtypes(include=['number']).columns)
            }
        elif isinstance(data, dict):
            result = {
                "data_type": "Dictionary",
                "keys": list(data.keys()),
                "size": len(data)
            }
        else:
            result = {
                "data_type": type(data).__name__,
                "size": len(str(data)) if hasattr(data, '__len__') else "N/A",
                "content_preview": str(data)[:100] + "..." if len(str(data)) > 100 else str(data)
            }
        
        # Add any additional parameters
        result.update(kwargs)
        return result
'''
    
    # Save the sample plugin
    plugins_dir = Path(__file__).resolve().parents[1] / "src" / "unimelb_phd_phase_1" / "plugins"
    sample_plugin_file = plugins_dir / "sample_enhanced_plugin.py"
    
    with open(sample_plugin_file, 'w') as f:
        f.write(plugin_content.strip())
    
    print(f"Created sample enhanced plugin at {sample_plugin_file}")
    return sample_plugin_file


def main():
    """Main function to demonstrate plugin systems."""
    parser = argparse.ArgumentParser(description="Demonstrate plugin system functionality")
    parser.add_argument("--basic", action="store_true", help="Demonstrate basic plugin system")
    parser.add_argument("--enhanced", action="store_true", help="Demonstrate enhanced plugin system")
    parser.add_argument("--create-sample", action="store_true", help="Create a sample enhanced plugin")
    
    args = parser.parse_args()
    
    # If no arguments provided, run all demonstrations
    if not any([args.basic, args.enhanced, args.create_sample]):
        args.basic = True
        args.enhanced = True
        args.create_sample = True
    
    try:
        if args.create_sample:
            create_sample_enhanced_plugin()
        
        if args.basic:
            demonstrate_basic_plugin_system()
        
        if args.enhanced:
            demonstrate_enhanced_plugin_system()
        
        print("\nPlugin demonstration complete!")
        
    except Exception as e:
        print(f"Error during plugin demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())