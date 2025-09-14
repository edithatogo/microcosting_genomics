#!/usr/bin/env python3
"""
Model Consistency Analysis Script

This script analyzes the consistency of categories and subcategories across
the five genomic testing models to establish a baseline for standardization.

Models analyzed:
- Panel (Targeted gene panel testing)
- WES (P) (Whole Exome Sequencing - Proband)
- WES (T) (Whole Exome Sequencing - Trio)
- WGS (Whole Genome Sequencing - Singleton)
- WGS (T) (Whole Genome Sequencing - Trio)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Set
from collections import defaultdict, Counter
from dataclasses import dataclass

@dataclass
class ModelAnalysis:
    """Container for model analysis results."""
    name: str
    categories: Set[str]
    subcategories: Dict[str, Set[str]]
    total_rows: int
    unique_combinations: int

class ModelConsistencyAnalyzer:
    """Analyzes consistency across genomic testing models."""

    def __init__(self, data_path: str = "data/Detailed Table.csv"):
        self.data_path = Path(data_path)
        self.models = [
            "Panel",
            "WES (P)",  # Whole Exome Sequencing - Proband
            "WES (T)",  # Whole Exome Sequencing - Trio
            "WGS",      # Whole Genome Sequencing - Singleton
            "WGS (T)"   # Whole Genome Sequencing - Trio
        ]

    def load_data(self) -> pd.DataFrame:
        """Load the detailed table data."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        # Read the CSV with proper header handling
        df = pd.read_csv(self.data_path, header=None)

        # Find the actual header row (should contain 'Test', 'Category', 'Sub-Category')
        header_row_idx = None
        for i, row in df.iterrows():
            if 'Test' in str(row.values) and 'Category' in str(row.values):
                header_row_idx = i
                break

        if header_row_idx is None:
            raise ValueError("Could not find header row with 'Test' and 'Category' columns")

        # Read again with the correct header
        df = pd.read_csv(self.data_path, header=header_row_idx)
        return df

    def extract_model_data(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Extract data for each model."""
        model_data = {}

        # Find all rows with non-empty Test values
        test_rows = df[df['Test'].notna()].index.tolist()

        for i, row_idx in enumerate(test_rows):
            test_value = df.loc[row_idx, 'Test']

            if test_value in self.models:
                # Collect all rows for this test until the next test or end
                start_idx = row_idx
                end_idx = test_rows[i + 1] if i + 1 < len(test_rows) else len(df)

                # Get all rows between this test and the next
                test_df = df.loc[start_idx:end_idx-1].copy()

                # Fill forward the Test value for rows that belong to this test
                test_df['Test'] = test_df['Test'].fillna(test_value)

                model_data[test_value] = test_df

        return model_data

    def analyze_model_categories(self, model_df: pd.DataFrame) -> ModelAnalysis:
        """Analyze categories and subcategories for a single model."""
        # Get unique categories
        categories = set(model_df['Category'].dropna().unique())

        # Get subcategories by category
        subcategories = defaultdict(set)
        for _, row in model_df.iterrows():
            category = row['Category']
            subcategory = row['Sub-Category']
            if pd.notna(category) and pd.notna(subcategory):
                subcategories[category].add(subcategory)

        # Calculate metrics
        total_rows = len(model_df)
        unique_combinations = len(model_df.groupby(['Category', 'Sub-Category']).size())

        return ModelAnalysis(
            name=model_df['Test'].iloc[0] if not model_df.empty else "Unknown",
            categories=categories,
            subcategories=dict(subcategories),
            total_rows=total_rows,
            unique_combinations=unique_combinations
        )

    def analyze_all_models(self) -> Dict[str, ModelAnalysis]:
        """Analyze all models and return results."""
        df = self.load_data()
        model_data = self.extract_model_data(df)

        results = {}
        for model_name, model_df in model_data.items():
            results[model_name] = self.analyze_model_categories(model_df)

        return results

    def calculate_consistency_metrics(self, analyses: Dict[str, ModelAnalysis]) -> Dict:
        """Calculate consistency metrics across all models."""
        if not analyses:
            return {}

        # Get all unique categories across models
        all_categories = set()
        for analysis in analyses.values():
            all_categories.update(analysis.categories)

        # Calculate category overlap
        category_counts = Counter()
        for analysis in analyses.values():
            for category in analysis.categories:
                category_counts[category] += 1

        # Calculate subcategory consistency
        subcategory_consistency = {}
        for category in all_categories:
            models_with_category = [
                analysis for analysis in analyses.values()
                if category in analysis.categories
            ]

            if len(models_with_category) > 1:
                # Get all subcategories for this category across models
                all_subcats = set()
                for analysis in models_with_category:
                    all_subcats.update(analysis.subcategories.get(category, set()))

                # Calculate overlap
                subcat_counts = Counter()
                for analysis in models_with_category:
                    for subcat in analysis.subcategories.get(category, set()):
                        subcat_counts[subcat] += 1

                max_models = len(models_with_category)
                common_subcats = sum(1 for count in subcat_counts.values() if count == max_models)
                total_subcats = len(subcat_counts)

                subcategory_consistency[category] = {
                    'total_subcategories': total_subcats,
                    'common_subcategories': common_subcats,
                    'consistency_ratio': common_subcats / total_subcats if total_subcats > 0 else 0,
                    'models_with_category': len(models_with_category)
                }

        return {
            'total_categories': len(all_categories),
            'categories_by_model': {name: len(analysis.categories) for name, analysis in analyses.items()},
            'category_overlap': dict(category_counts),
            'subcategory_consistency': subcategory_consistency,
            'model_count': len(analyses)
        }

    def generate_report(self, analyses: Dict[str, ModelAnalysis], metrics: Dict) -> str:
        """Generate a comprehensive analysis report."""
        report = []
        report.append("# Model Consistency Analysis Report")
        report.append(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary section
        report.append("## Summary")
        report.append(f"- **Models Analyzed**: {len(analyses)}")
        report.append(f"- **Total Categories**: {metrics.get('total_categories', 0)}")
        report.append("")

        # Model breakdown
        report.append("## Model Breakdown")
        for name, analysis in analyses.items():
            report.append(f"### {name}")
            report.append(f"- **Total Rows**: {analysis.total_rows}")
            report.append(f"- **Categories**: {len(analysis.categories)}")
            report.append(f"- **Unique Category-Subcategory Combinations**: {analysis.unique_combinations}")
            report.append(f"- **Categories**: {', '.join(sorted(analysis.categories))}")
            report.append("")

            if analysis.subcategories:
                report.append("**Subcategories by Category:**")
                for category, subcats in sorted(analysis.subcategories.items()):
                    report.append(f"  - **{category}**: {', '.join(sorted(subcats))}")
                report.append("")

        # Consistency analysis
        report.append("## Consistency Analysis")
        report.append("### Category Overlap")
        for category, count in sorted(metrics.get('category_overlap', {}).items()):
            report.append(f"- {category}: {count} models ({(count / len(analyses)) * 100 if analyses else 0:.1f}%)")
        report.append("")

        # Subcategory consistency
        if metrics.get('subcategory_consistency'):
            report.append("### Subcategory Consistency")
            for category, data in sorted(metrics['subcategory_consistency'].items()):
                report.append(f"**{category}**:")
                report.append(f"  - Models with category: {data['models_with_category']}")
                report.append(f"  - Total subcategories: {data['total_subcategories']}")
                report.append(f"  - Common subcategories: {data['common_subcategories']}")
                report.append(f"  - Consistency: {data['consistency_ratio'] * 100:.1f}%")
                report.append("")

        # Recommendations
        report.append("## Recommendations for Standardization")
        report.append("### High Priority Categories (>80% consistency)")
        high_priority = [
            cat for cat, data in metrics.get('subcategory_consistency', {}).items()
            if data['consistency_ratio'] >= 0.8
        ]
        if high_priority:
            for category in sorted(high_priority):
                report.append(f"- {category}")
        else:
            report.append("- No categories with >80% consistency found")
        report.append("")

        report.append("### Medium Priority Categories (50-80% consistency)")
        medium_priority = [
            cat for cat, data in metrics.get('subcategory_consistency', {}).items()
            if 0.5 <= data['consistency_ratio'] < 0.8
        ]
        if medium_priority:
            for category in sorted(medium_priority):
                report.append(f"- {category}")
        else:
            report.append("- No categories with 50-80% consistency found")
        report.append("")

        report.append("### Low Priority Categories (<50% consistency)")
        low_priority = [
            cat for cat, data in metrics.get('subcategory_consistency', {}).items()
            if data['consistency_ratio'] < 0.5
        ]
        if low_priority:
            for category in sorted(low_priority):
                report.append(f"- {category}")
        else:
            report.append("- No categories with <50% consistency found")
        report.append("")

        return "\n".join(report)

    def save_report(self, report: str, output_path: str = "docs/model_standardization.md"):
        """Save the analysis report to a file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"Report saved to: {output_file}")

def main():
    """Main execution function."""
    analyzer = ModelConsistencyAnalyzer()

    try:
        # Analyze all models
        print("Loading data...")
        analyses = analyzer.analyze_all_models()

        if not analyses:
            print("No model data found. Please check the data file and model names.")
            return

        print(f"Found {len(analyses)} models: {', '.join(analyses.keys())}")

        # Calculate consistency metrics
        print("Calculating consistency metrics...")
        metrics = analyzer.calculate_consistency_metrics(analyses)

        # Generate and save report
        print("Generating report...")
        report = analyzer.generate_report(analyses, metrics)
        analyzer.save_report(report)

        print("Analysis complete!")
        print(f"Models analyzed: {len(analyses)}")
        print(f"Total categories found: {metrics.get('total_categories', 0)}")

    except Exception as e:
        print(f"Error during analysis: {e}")
        raise

if __name__ == "__main__":
    main()
