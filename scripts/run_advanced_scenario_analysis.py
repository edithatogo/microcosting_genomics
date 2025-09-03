#!/usr/bin/env python3
"""
Script to run advanced scenario analysis with sophisticated comparison features.
"""

import sys
from pathlib import Path
import pandas as pd
import argparse
import json

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from unimelb_phd_phase_1.advanced_scenario_modeling import AdvancedScenarioManager, create_advanced_scenarios
from unimelb_phd_phase_1.visualization import load_prepared_data


def main():
    """Main function to run advanced scenario analysis."""
    parser = argparse.ArgumentParser(description="Run advanced scenario analysis for microcosting data")
    parser.add_argument("--data-dir", help="Path to prepared data directory")
    parser.add_argument("--output-dir", help="Path to output directory for results")
    parser.add_argument("--scenario", help="Specific scenario to run (default: run all advanced scenarios)")
    parser.add_argument("--compare", nargs="+", help="Scenarios to compare")
    parser.add_argument("--sensitivity", action="store_true", help="Run sensitivity analysis")
    parser.add_argument("--probabilistic", action="store_true", help="Run probabilistic analysis")
    parser.add_argument("--export-formats", nargs="+", default=["csv"], 
                       help="Formats to export results (csv, json, parquet)")
    
    args = parser.parse_args()
    
    print("Running advanced scenario analysis...")
    
    try:
        # Load data
        if args.data_dir:
            data_dir = Path(args.data_dir)
        else:
            data_dir = Path(__file__).resolve().parents[1] / "data" / "prepared"
        
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = Path(__file__).resolve().parents[1] / "reports" / "advanced_scenarios"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Loading data from {data_dir}")
        data_dict = load_prepared_data(data_dir)
        print(f"Loaded {len(data_dict)} data tables")
        
        # Create advanced scenario manager
        scenario_manager = AdvancedScenarioManager(data_dict)
        
        # Add advanced scenarios
        advanced_scenarios = create_advanced_scenarios()
        for name, scenario in advanced_scenarios.items():
            scenario_manager.add_advanced_scenario(scenario)
        
        # Determine which scenarios to run
        if args.scenario:
            scenarios_to_run = [args.scenario]
        else:
            scenarios_to_run = list(advanced_scenarios.keys())
        
        # Run scenarios
        print(f"Running scenarios: {scenarios_to_run}")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.advanced_scenarios:
                print(f"Running scenario: {scenario_name}")
                results = scenario_manager.run_scenario_analysis(scenario_name)
                print(f"  Processed {len(results)} tables")
            else:
                print(f"Warning: Scenario '{scenario_name}' not found")
        
        # Run sensitivity analysis if requested
        if args.sensitivity:
            print("Running sensitivity analysis...")
            for scenario_name in scenarios_to_run:
                if scenario_name in scenario_manager.advanced_scenarios:
                    scenario = scenario_manager.advanced_scenarios[scenario_name]
                    if scenario.sensitivity_parameters:
                        for param, (param_min, param_max) in scenario.sensitivity_parameters.items():
                            print(f"  Analyzing sensitivity for {param} in {scenario_name}")
                            try:
                                sensitivity_results = scenario_manager.run_sensitivity_analysis(
                                    scenario_name, param, param_min, param_max, 10
                                )
                                print(f"    Sensitivity analysis for {param} completed")
                            except Exception as e:
                                print(f"    Error in sensitivity analysis for {param}: {e}")
                    else:
                        print(f"  No sensitivity parameters defined for {scenario_name}")
        
        # Run probabilistic analysis if requested
        if args.probabilistic:
            print("Running probabilistic analysis...")
            for scenario_name in scenarios_to_run:
                if scenario_name in scenario_manager.advanced_scenarios:
                    print(f"  Running Monte Carlo simulation for {scenario_name}")
                    try:
                        prob_results = scenario_manager.run_probabilistic_analysis(
                            scenario_name, iterations=100
                        )
                        print(f"    Probabilistic analysis for {scenario_name} completed with {len(prob_results)} iterations")
                    except Exception as e:
                        print(f"    Error in probabilistic analysis for {scenario_name}: {e}")
        
        # Compare scenarios if requested
        if args.compare:
            print(f"Comparing scenarios: {args.compare}")
            # Compare scenarios for the detailed table
            if 'detailed_table' in data_dict:
                try:
                    detailed_comparison = scenario_manager.compare_scenarios_detailed(
                        args.compare, 'detailed_table'
                    )
                    
                    # Save detailed comparison to files
                    comparison_dir = output_dir / "detailed_comparisons"
                    comparison_dir.mkdir(exist_ok=True)
                    
                    for column, df in detailed_comparison.items():
                        # Sanitize column name for filename
                        safe_column = "".join(c for c in column if c.isalnum() or c in (" ", "-", "_")).rstrip()
                        safe_column = safe_column.replace(" ", "_").replace("/", "_per_")
                        
                        # Save as CSV
                        csv_file = comparison_dir / f"detailed_comparison_{safe_column}.csv"
                        df.to_csv(csv_file)
                        
                        # Save as JSON
                        json_file = comparison_dir / f"detailed_comparison_{safe_column}.json"
                        df.to_json(json_file, indent=2)
                    
                    print(f"Saved detailed comparisons to {comparison_dir}")
                    
                except Exception as e:
                    print(f"Error in detailed comparison: {e}")
        
        # Export results if requested
        print(f"Exporting results in formats: {args.export_formats}")
        for scenario_name in scenarios_to_run:
            if scenario_name in scenario_manager.results:
                try:
                    scenario_manager.export_scenario_results(
                        scenario_name, 
                        output_dir / "exported_results" / scenario_name,
                        formats=args.export_formats
                    )
                    print(f"  Exported results for {scenario_name}")
                except Exception as e:
                    print(f"  Error exporting results for {scenario_name}: {e}")
        
        # Generate advanced report
        report_file = output_dir / "advanced_scenario_analysis_report.md"
        print(f"Generating advanced report in {report_file}")
        try:
            report = scenario_manager.generate_advanced_report(scenarios_to_run, report_file)
            print("Advanced report generated successfully")
        except Exception as e:
            print(f"Error generating advanced report: {e}")
            # Generate a simpler report as fallback
            fallback_report = output_dir / "scenario_analysis_report.md"
            print(f"Generating fallback report in {fallback_report}")
            report = scenario_manager.generate_scenario_report(scenarios_to_run, fallback_report)
        
        print("Advanced scenario analysis complete!")
        print(f"Results saved to {output_dir}")
        
        # List generated files
        print("\nGenerated files:")
        for item in output_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(output_dir)
                print(f"  {relative_path}")
        
    except Exception as e:
        print(f"Error running advanced scenario analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())