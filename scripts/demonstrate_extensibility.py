#!/usr/bin/env python3
"""
Script to demonstrate the Extensibility Framework.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.extensibility_framework import ExtensibilityFramework, ExampleAnalysisExtension, ExampleVisualizationExtension
from unimelb_phd_phase_1.data_manager import DataManager


def main():
    """Main function to demonstrate the extensibility framework."""
    print("Demonstrating Extensibility Framework...")
    
    try:
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
        print(f"\nRegistered extensions: {len(extensions)}")
        for extension in extensions:
            print(f"  - {extension['name']} v{extension['version']}: {extension['description']}")
            print(f"    Type: {extension['type']}")
            print(f"    Author: {extension['author']}")
            print(f"    License: {extension['license']}")
            print(f"    Tags: {extension['tags']}")
            print(f"    Enabled: {extension['enabled']}")
            print()
        
        # Execute extension methods
        print("Executing extension methods...")
        try:
            result = framework.execute_extension_method("example_analysis_extension", "analyze", "test data")
            print(f"Analysis result: {result}")
            
            viz_result = framework.execute_extension_method("example_visualization_extension", "visualize", "test data")
            print(f"Visualization result: {viz_result}")
        except Exception as e:
            print(f"Error executing extension method: {e}")
        
        # Get extensions by type
        print("\nExtensions by type:")
        analysis_extensions = framework.get_extensions_by_type("analysis")
        print(f"Analysis extensions: {len(analysis_extensions)}")
        
        visualization_extensions = framework.get_extensions_by_type("visualization")
        print(f"Visualization extensions: {len(visualization_extensions)}")
        
        # Validate dependencies
        print("\nValidating extension dependencies...")
        dependency_issues = framework.validate_extension_dependencies()
        if dependency_issues:
            print("Dependency issues found:")
            for ext_name, missing_deps in dependency_issues.items():
                print(f"  {ext_name}: missing {missing_deps}")
        else:
            print("All extension dependencies are satisfied.")
        
        # Generate framework report
        report = []
        report.append("# Extensibility Framework Demonstration Report\n")
        report.append("## Summary\n")
        report.append("This report demonstrates the capabilities of the extensibility framework.\n")
        
        report.append("## Registered Extensions\n")
        for extension in extensions:
            report.append(f"- **{extension['name']}** v{extension['version']}")
            report.append(f"  - Description: {extension['description']}")
            report.append(f"  - Type: {extension['type']}")
            report.append(f"  - Author: {extension['author']}")
            report.append(f"  - License: {extension['license']}")
            report.append(f"  - Enabled: {extension['enabled']}")
            report.append("")
        
        report.append("## Extension Execution Results\n")
        report.append(f"Analysis result: {result}\n")
        report.append(f"Visualization result: {viz_result}\n")
        
        report.append("## Dependency Validation\n")
        if dependency_issues:
            report.append("Dependency issues found:")
            for ext_name, missing_deps in dependency_issues.items():
                report.append(f"- {ext_name}: missing {missing_deps}")
        else:
            report.append("All extension dependencies are satisfied.")
        
        report_str = "\n".join(report)
        print("\n" + report_str)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "extensibility_framework_demo.md"
        with open(output_file, 'w') as f:
            f.write(report_str)
        print(f"\nReport saved to {output_file}")
        
        # Cleanup
        framework.cleanup()
        print("\nDemonstration complete.")
        
    except Exception as e:
        print(f"Error in extensibility framework demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()