#!/usr/bin/env python3
# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Script to demonstrate the enhanced plugin system functionality."""

import argparse
import json
import logging
import sys
import traceback
from pathlib import Path

from genomics_microcosting.enhanced_plugin_system import EnhancedPluginManager
from genomics_microcosting.plugin_system import PluginManager

logger = logging.getLogger(__name__)


def demonstrate_basic_plugin_system() -> None:
    """Demonstrate the basic plugin system."""
    sys.stdout.write("=== Basic Plugin System Demonstration ===" + "\n")

    # Create plugin manager
    plugin_manager = PluginManager()

    # Load all plugins
    sys.stdout.write("Loading plugins..." + "\n")
    plugin_manager.load_all_plugins()

    # List plugins
    plugins = plugin_manager.list_plugins()
    sys.stdout.write(f"\nFound {len(plugins)} plugins:" + "\n")
    for plugin in plugins:
        sys.stdout.write(
            f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}\n",
        )
        sys.stdout.write(f"    Type: {plugin['type']}" + "\n")
        sys.stdout.write(f"    Enabled: {plugin['enabled']}" + "\n")

    # Execute example plugin methods if available
    for plugin in plugins:
        plugin_name = plugin["name"]
        plugin_type = plugin["type"]

        try:
            if plugin_type == "ExampleAnalysisPlugin":
                result = plugin_manager.execute_plugin_method(
                    plugin_name,
                    "analyze",
                    "sample data",
                )
                sys.stdout.write(
                    f"\nAnalysis result from {plugin_name}: {result}" + "\n",
                )
            elif plugin_type == "ExampleVisualizationPlugin":
                result = plugin_manager.execute_plugin_method(
                    plugin_name,
                    "visualize",
                    "sample data",
                )
                sys.stdout.write(
                    f"\nVisualization result from {plugin_name}: {result}" + "\n",
                )
        except Exception as e:
            logger.exception("Could not complete demonstrate basic plugin system")
            sys.stdout.write(f"\nError executing {plugin_name}: {e}" + "\n")


def _demonstrate_plugin_methods(
    plugin_manager: EnhancedPluginManager,
    all_plugins: list[dict],
) -> None:
    # Execute plugin methods
    for plugin in all_plugins:
        plugin_name = plugin["name"]

        try:
            if "analysis" in plugin["tags"]:
                result = plugin_manager.execute_plugin_method(
                    plugin_name,
                    "analyze",
                    "sample data",
                    detailed=True,
                )
                sys.stdout.write(
                    f"\nEnhanced analysis result from {plugin_name}: {result}" + "\n",
                )
            elif "visualization" in plugin["tags"]:
                result = plugin_manager.execute_plugin_method(
                    plugin_name,
                    "visualize",
                    "sample data",
                    output_format="html",
                )
                sys.stdout.write(
                    f"\nEnhanced visualization result from {plugin_name}: {result}\n",
                )
        except Exception as e:
            logger.exception("Could not complete demonstrate enhanced plugin system")
            sys.stdout.write(f"\nError executing {plugin_name}: {e}" + "\n")


def demonstrate_enhanced_plugin_system() -> None:
    """Demonstrate the enhanced plugin system."""
    sys.stdout.write("\n=== Enhanced Plugin System Demonstration ===" + "\n")

    # Create enhanced plugin manager
    config_file = Path(__file__).resolve().parents[1] / "config" / "plugin_config.json"
    plugin_manager = EnhancedPluginManager(config_file=config_file)

    # Load all plugins
    sys.stdout.write("Loading enhanced plugins..." + "\n")
    load_results = plugin_manager.load_all_plugins()
    sys.stdout.write(f"Loaded plugins: {load_results['loaded']}" + "\n")
    if load_results["failed"]:
        sys.stdout.write(f"Failed to load plugins: {load_results['failed']}" + "\n")

    # List plugins with tag filtering
    sys.stdout.write("\nAll plugins:" + "\n")
    all_plugins = plugin_manager.list_plugins()
    for plugin in all_plugins:
        sys.stdout.write(
            f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}\n",
        )
        sys.stdout.write(f"    Tags: {plugin['tags']}" + "\n")
        sys.stdout.write(f"    Author: {plugin['author']}" + "\n")
        sys.stdout.write(f"    Enabled: {plugin['enabled']}" + "\n")
        sys.stdout.write(f"    Initialized: {plugin['initialized']}" + "\n")

    # List plugins by tag
    sys.stdout.write("\nAnalysis plugins:" + "\n")
    analysis_plugins = plugin_manager.list_plugins(filter_tags=["analysis"])
    for plugin in analysis_plugins:
        sys.stdout.write(f"  - {plugin['name']}" + "\n")

    sys.stdout.write("\nVisualization plugins:" + "\n")
    viz_plugins = plugin_manager.list_plugins(filter_tags=["visualization"])
    for plugin in viz_plugins:
        sys.stdout.write(f"  - {plugin['name']}" + "\n")

    _demonstrate_plugin_methods(plugin_manager, all_plugins)

    # Execute plugins by tag
    sys.stdout.write("\nExecuting all analysis plugins:" + "\n")
    analysis_results = plugin_manager.execute_plugins_by_tag(
        "analysis",
        "analyze",
        "test data",
    )
    for plugin_name, result in analysis_results.items():
        sys.stdout.write(f"  {plugin_name}: {result}" + "\n")

    # Get plugin statistics
    stats = plugin_manager.get_plugin_statistics()
    sys.stdout.write("\nPlugin statistics:" + "\n")
    sys.stdout.write(str(json.dumps(stats, indent=2)) + "\n")

    # Export plugin metadata
    sys.stdout.write("\nExporting plugin metadata..." + "\n")
    for plugin in all_plugins:
        plugin_instance = plugin_manager.get_plugin(plugin["name"])
        if plugin_instance:
            metadata = plugin_instance.export_metadata()
            sys.stdout.write(
                f"  {plugin['name']} metadata: {json.dumps(metadata, indent=2)}" + "\n",
            )


def create_sample_enhanced_plugin() -> Path:
    """Create a sample enhanced plugin."""
    sys.stdout.write("\n=== Creating Sample Enhanced Plugin ===" + "\n")

    plugin_content = '''
"""Sample enhanced cost analysis plugin."""

import pandas as pd
from typing import Any, Dict
from genomics_microcosting.enhanced_plugin_system import AnalysisPlugin  # noqa: E402


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
            text = str(data)
            result = {
                "data_type": type(data).__name__,
                "size": len(text) if hasattr(data, '__len__') else "N/A",
                "content_preview": text[:100] + "..." if len(text) > 100 else text,
            }

        # Add any additional parameters
        result.update(kwargs)
        return result
'''

    # Save the sample plugin
    plugins_dir = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "genomics_microcosting"
        / "plugins"
    )
    sample_plugin_file = plugins_dir / "sample_enhanced_plugin.py"

    with Path(sample_plugin_file).open("w") as f:
        f.write(plugin_content.strip())

    sys.stdout.write(f"Created sample enhanced plugin at {sample_plugin_file}" + "\n")
    return sample_plugin_file


def main() -> int:
    """Demonstrate plugin systems."""
    parser = argparse.ArgumentParser(
        description="Demonstrate plugin system functionality",
    )
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Demonstrate basic plugin system",
    )
    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Demonstrate enhanced plugin system",
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample enhanced plugin",
    )

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

        sys.stdout.write("\nPlugin demonstration complete!" + "\n")

    except Exception as e:
        logger.exception("Could not complete demonstrate plugins")
        sys.stdout.write(f"Error during plugin demonstration: {e}" + "\n")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
