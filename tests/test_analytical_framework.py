# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test suite for the analytical framework modules."""

import unittest

from genomics_microcosting.break_even_analysis import BreakEvenAnalyzer
from genomics_microcosting.budget_impact_analysis import BudgetImpactAnalyzer
from genomics_microcosting.comprehensive_reporting import ComprehensiveReporter
from genomics_microcosting.cost_driver_analysis import CostDriverAnalyzer
from genomics_microcosting.data_manager import DataManager
from genomics_microcosting.dsa_analysis import DSAAnalyzer
from genomics_microcosting.psa_analysis import PSAAnalyzer
from genomics_microcosting.voi_analysis import VOIAnalyzer
from tests.checks import require_runtime_instance


class TestAnalyticalFramework(unittest.TestCase):
    """Test cases for the analytical framework modules."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.data_manager = DataManager()
        self.cost_driver_analyzer = CostDriverAnalyzer(self.data_manager)
        self.dsa_analyzer = DSAAnalyzer(self.data_manager)
        self.psa_analyzer = PSAAnalyzer(self.data_manager)
        self.voi_analyzer = VOIAnalyzer(self.data_manager)
        self.budget_impact_analyzer = BudgetImpactAnalyzer(self.data_manager)
        self.break_even_analyzer = BreakEvenAnalyzer(self.data_manager)
        self.comprehensive_reporter = ComprehensiveReporter(self.data_manager)

    def test_data_manager_initialization(self) -> None:
        """Test that DataManager initializes correctly."""
        require_runtime_instance(self.data_manager, DataManager)
        if not (hasattr(self.data_manager, "load_sheet")):
            raise AssertionError
        if not (hasattr(self.data_manager, "save_sheet")):
            raise AssertionError

    def test_cost_driver_analyzer_initialization(self) -> None:
        """Test that CostDriverAnalyzer initializes correctly."""
        require_runtime_instance(self.cost_driver_analyzer, CostDriverAnalyzer)
        if not (hasattr(self.cost_driver_analyzer, "generate_cost_driver_report")):
            raise AssertionError

    def test_dsa_analyzer_initialization(self) -> None:
        """Test that DSAAnalyzer initializes correctly."""
        require_runtime_instance(self.dsa_analyzer, DSAAnalyzer)
        if not (hasattr(self.dsa_analyzer, "generate_dsa_report")):
            raise AssertionError

    def test_psa_analyzer_initialization(self) -> None:
        """Test that PSAAnalyzer initializes correctly."""
        require_runtime_instance(self.psa_analyzer, PSAAnalyzer)
        if not (hasattr(self.psa_analyzer, "generate_psa_report")):
            raise AssertionError

    def test_voi_analyzer_initialization(self) -> None:
        """Test that VOIAnalyzer initializes correctly."""
        require_runtime_instance(self.voi_analyzer, VOIAnalyzer)
        if not (hasattr(self.voi_analyzer, "generate_voi_report")):
            raise AssertionError

    def test_budget_impact_analyzer_initialization(self) -> None:
        """Test that BudgetImpactAnalyzer initializes correctly."""
        require_runtime_instance(self.budget_impact_analyzer, BudgetImpactAnalyzer)
        if not (hasattr(self.budget_impact_analyzer, "generate_budget_impact_report")):
            raise AssertionError

    def test_break_even_analyzer_initialization(self) -> None:
        """Test that BreakEvenAnalyzer initializes correctly."""
        require_runtime_instance(self.break_even_analyzer, BreakEvenAnalyzer)
        if not (hasattr(self.break_even_analyzer, "generate_break_even_report")):
            raise AssertionError

    def test_comprehensive_reporter_initialization(self) -> None:
        """Test that ComprehensiveReporter initializes correctly."""
        require_runtime_instance(self.comprehensive_reporter, ComprehensiveReporter)
        if not (hasattr(self.comprehensive_reporter, "generate_integrated_report")):
            raise AssertionError

    def test_cost_driver_report_generation(self) -> None:
        """Test that cost driver report can be generated."""
        report = self.cost_driver_analyzer.generate_cost_driver_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_dsa_report_generation(self) -> None:
        """Test that DSA report can be generated."""
        report = self.dsa_analyzer.generate_dsa_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_psa_report_generation(self) -> None:
        """Test that PSA report can be generated."""
        report = self.psa_analyzer.generate_psa_report(iterations=100)
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_voi_report_generation(self) -> None:
        """Test that VOI report can be generated."""
        report = self.voi_analyzer.generate_voi_report(iterations=100)
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_budget_impact_report_generation(self) -> None:
        """Test that budget impact report can be generated."""
        report = self.budget_impact_analyzer.generate_budget_impact_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_break_even_report_generation(self) -> None:
        """Test that break-even report can be generated."""
        report = self.break_even_analyzer.generate_break_even_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError

    def test_comprehensive_report_generation(self) -> None:
        """Test that comprehensive report can be generated."""
        report = self.comprehensive_reporter.generate_integrated_report()
        require_runtime_instance(report, str)
        if not ((len(report)) > (0)):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()
