#!/usr/bin/env python3
"""
Script to demonstrate the Configuration-driven Analysis Parameters System.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.analysis_config import AnalysisConfigurationManager


def main():
    """Main function to demonstrate the analysis configuration system."""
    print("Demonstrating Configuration-driven Analysis Parameters System...")
    
    try:
        # Create configuration manager
        config_manager = AnalysisConfigurationManager()
        
        # List available configurations
        print("\nAvailable configurations:")
        config_names = config_manager.list_configurations()
        for name in config_names:
            print(f"  - {name}")
        
        # Show details for a few configurations
        print("\nConfiguration details:")
        for config_name in ["cost_driver_analysis", "psa_analysis", "voi_analysis"]:
            config = config_manager.get_configuration(config_name)
            if config:
                print(f"\n{config_name}:")
                print(f"  Description: {config.description}")
                print(f"  Version: {config.version}")
                print(f"  Author: {config.author}")
                print(f"  Parameters ({len(config.parameters)}):")
                for param_name, parameter in config.parameters.items():
                    print(f"    {param_name}: {parameter.value} ({parameter.description})")
        
        # Demonstrate parameter access
        print("\nParameter access examples:")
        top_n_drivers = config_manager.get_parameter_value("cost_driver_analysis", "top_n_drivers", 10)
        print(f"Cost driver analysis top_n_drivers: {top_n_drivers}")
        
        monte_carlo_iterations = config_manager.get_parameter_value("psa_analysis", "monte_carlo_iterations", 1000)
        print(f"PSA analysis monte_carlo_iterations: {monte_carlo_iterations}")
        
        # Demonstrate parameter modification
        print("\nParameter modification examples:")
        success = config_manager.set_parameter_value("cost_driver_analysis", "top_n_drivers", 15)
        print(f"Setting top_n_drivers to 15: {'Success' if success else 'Failed'}")
        
        new_value = config_manager.get_parameter_value("cost_driver_analysis", "top_n_drivers")
        print(f"New value of top_n_drivers: {new_value}")
        
        # Demonstrate validation
        print("\nConfiguration validation:")
        validation_results = config_manager.validate_configuration("cost_driver_analysis")
        if validation_results["errors"]:
            print("Errors found:")
            for error in validation_results["errors"]:
                print(f"  - {error}")
        else:
            print("No validation errors found.")
        
        if validation_results["warnings"]:
            print("Warnings found:")
            for warning in validation_results["warnings"]:
                print(f"  - {warning}")
        
        # Generate configuration report
        report = config_manager.generate_config_report()
        print("\n" + "="*50)
        print("CONFIGURATION REPORT")
        print("="*50)
        print(report[:1000] + "..." if len(report) > 1000 else report)  # Show first 1000 chars
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "analysis_configuration_demo.md"
        config_manager.generate_config_report(output_file=str(output_file))
        print(f"\nReport saved to {output_file}")
        
        print("\nDemonstration complete.")
        
    except Exception as e:
        print(f"Error in analysis configuration demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()