#!/usr/bin/env python3
"""
Script to run scenario analysis for microcosting data.
"""

import sys
from pathlib import Path
import pandas as pd
import argparse

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.scenario_modeling import ScenarioManager, create_common_scenarios
from unimelb_phd_phase_1.visualization import load_prepared_data


def main():
    """Main function to run scenario analysis."""
    parser = argparse.ArgumentParser(description="Run scenario analysis for microcosting data")
    parser.add_argument("--data-dir", help="Path to prepared data directory")
    parser.add_argument("--output-dir", help="Path to output directory for results")
    parser.add_argument("--scenario", help="Specific scenario to run (default: run all common scenarios)")
    parser.add_argument("--compare", nargs="+", help="Scenarios to compare")
    
    args = parser.parse_args()
    
    print("Running scenario analysis...")
    
    try:
        # Load data
        if args.data_dir:
            data_dir = Path(args.data_dir)
        else:
            data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path(__file__).resolve().parents[1] / "reports" / "scenarios"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Loading data from {data_dir}")
        data_dict = load_prepared_data(data_dir)
        print(f"Loaded {len(data_dict)} data tables")
        
        # Create scenario manager
        scenario_manager = ScenarioManager(data_dict)
        
        # Add common scenarios
        common_scenarios = create_common_scenarios()
        for name, scenario in common_scenarios.items():
            scenario_manager.add_scenario(scenario)
        
        # Determine which scenarios to run
        if args.scenario:
            scenarios_to_run = [args.scenario]
        else:
            scenarios_to_run = list(common_scenarios.keys())
        
        # Run scenarios
        print(f"Running scenarios: {scenarios_to_run}")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.scenarios:
                print(f"Running scenario: {scenario_name}")
                results = scenario_manager.run_scenario_analysis(scenario_name)
                print(f"  Processed {len(results)} tables")
            else:
                print(f"Warning: Scenario '{scenario_name}' not found")
        
        # Compare scenarios if requested
        if args.compare:
            print(f"Comparing scenarios: {args.compare}")
            # Compare scenarios for the detailed table
            if 'detailed_table' in data_dict:
                try:
                    comparison = scenario_manager.compare_scenarios(
                        args.compare, 'detailed_table'
                    )
                    
                    # Save comparison to CSV
                    comparison_file = output_dir / "scenario_comparison.csv"
                    comparison.to_csv(comparison_file, index=False)
                    print(f"Saved comparison to {comparison_file}")
                    
                    # Print summary
                    print("\nScenario Comparison Summary:")
                    print(comparison.to_string(index=False))
                    
                except Exception as e:
                    print(f"Error comparing scenarios: {e}")
        
        # Generate report
        report_file = output_dir / "scenario_analysis_report.md"
        print(f"Generating report in {report_file}")
        report = scenario_manager.generate_scenario_report(scenarios_to_run, report_file)
        
        print("Scenario analysis complete!")
        print(f"Results saved to {output_dir}")
        
    except Exception as e:
        print(f"Error running scenario analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())