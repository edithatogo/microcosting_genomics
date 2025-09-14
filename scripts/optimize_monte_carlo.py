#!/usr/bin/env python3
"""
Script to perform Monte Carlo Simulation Optimization.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_path = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_path))

from genomics_microcosting.monte_carlo_optimizer import MonteCarloOptimizer  # noqa: E402
from genomics_microcosting.data_manager import DataManager  # noqa: E402


def main():
    """Main function to run Monte Carlo optimization."""
    print("Running Monte Carlo Simulation Optimization...")
    
    try:
        # Initialize data manager
        data_manager = DataManager()
        
        # Initialize optimizer
        optimizer = MonteCarloOptimizer(data_manager)
        
        # Generate report
        report = optimizer.generate_optimization_report()
        print(report)
        
        # Save report to file
        output_file = Path(__file__).resolve().parents[1] / "reports" / "monte_carlo_optimization.md"
        optimizer.generate_optimization_report(output_file=str(output_file))
        print(f"Report saved to {output_file}")
        
    except Exception as e:
        print(f"Error in Monte Carlo optimization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()