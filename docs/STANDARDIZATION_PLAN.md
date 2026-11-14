# Genomic Microcosting Model Standardization Plan

## Overview

This document outlines a comprehensive plan to standardize the microcosting approach across five genomic testing models while maintaining fidelity to the original Excel implementations. The plan addresses both standardization needs and enhancements for broader adoption by genomic labs worldwide.

## Background

The microcosting model currently supports five genomic testing models:

- **Panel** - Targeted gene panel testing
- **Exome-Sequencing-Proband** - Single individual exome sequencing
- **Exome-Sequencing-Trio** - Family trio exome sequencing
- **Genome-Sequencing-Singleton** - Single individual genome sequencing
- **Genome-Sequencing-Trio** - Family trio genome sequencing

Each model should have consistent categories and subcategories while allowing for model-specific variations.

## Phase 1: Standardization Analysis (1-2 weeks)

### Objective

Establish baseline consistency across models and identify areas requiring standardization.

### Tasks

#### 1.1 Run Consistency Analysis

- Execute `scripts/analyze_model_consistency.py` to quantify current variations
- Identify common vs. model-specific categories and subcategories
- Document discrepancies in `docs/model_standardization.md`

#### 1.2 Define Standard Taxonomy

Create standardized category hierarchy in `config.yaml`:

```yaml
# Standard categories across all models
standard_categories:
  - "Labor"
  - "Equipment"
  - "Consumables"
  - "Overheads"
  - "Data Analysis"

# Standard subcategories by category
standard_subcategories:
  Labor:
    - "Technician"
    - "Bioinformatician"
    - "Scientist"
    - "Manager"
  Equipment:
    - "Sequencer"
    - "Storage"
    - "Compute"
  Consumables:
    - "Reagents"
    - "Libraries"
    - "Flow Cells"
  Overheads:
    - "Facility"
    - "Administration"
    - "Quality Control"
  Data_Analysis:
    - "Primary Analysis"
    - "Secondary Analysis"
    - "Storage"
```

#### 1.3 Validation Framework

- Implement automated validation to ensure standardized models produce identical results to originals
- Extend `validate_engine.py` for multi-model comparison
- Create baseline performance metrics for each model

## Phase 2: Implementation of Standardization (2-4 weeks)

### Core Standardization Features

#### 2.1 Unified Data Schema

- Update `sheet_manager.py` to enforce standard categories/subcategories
- Add validation in `prepare_data.py` to flag non-standard entries
- Implement automatic categorization mapping

#### 2.2 Model-Specific Adaptations

Create inheritance pattern for model configurations:

```python
# src/unimelb_phd_phase_1/model_config.py
class GenomicModelConfig:
    """Configuration manager for genomic testing models."""

    def __init__(self, model_type):
        self.base_categories = [
            "Labor",
            "Equipment",
            "Consumables",
            "Overheads",
            "Data Analysis",
        ]
        self.model_specific = self._get_model_specific(model_type)

    def _get_model_specific(self, model_type):
        """Get model-specific categories and subcategories."""
        specifics = {
            "genome-sequencing-trio": ["Data Storage", "Cloud Compute"],
            "panel": ["Target Enrichment"],
            "exome-sequencing-trio": ["Family Analysis"],
        }
        return specifics.get(model_type, [])

    def get_allowed_categories(self):
        """Get all allowed categories for this model."""
        return self.base_categories + self.model_specific
```

#### 2.3 Automated Standardization Script

```python
# scripts/standardize_models.py
import pandas as pd
from pathlib import Path
from typing import Dict, List


class ModelStandardizer:
    """Standardize categories and subcategories across models."""

    def __init__(self):
        self.category_mappings = self._load_category_mappings()
        self.subcategory_mappings = self._load_subcategory_mappings()

    def standardize_model(self, model_name: str) -> pd.DataFrame:
        """Standardize a single model's data."""
        input_file = Path(f"data/prepared/detailed_table_{model_name}.parquet")
        output_file = Path(f"data/standardized/detailed_table_{model_name}.parquet")

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        df = pd.read_parquet(input_file)

        # Apply standardization
        df = self._apply_category_mappings(df, model_name)
        df = self._apply_subcategory_mappings(df, model_name)

        # Validate against standards
        self._validate_against_standards(df, model_name)

        # Save standardized version
        output_file.parent.mkdir(exist_ok=True)
        df.to_parquet(output_file)

        return df

    def _apply_category_mappings(
        self, df: pd.DataFrame, model_name: str
    ) -> pd.DataFrame:
        """Map model-specific categories to standard ones."""
        if model_name in self.category_mappings:
            mapping = self.category_mappings[model_name]
            df["Category"] = df["Category"].map(mapping).fillna(df["Category"])
        return df

    def _apply_subcategory_mappings(
        self, df: pd.DataFrame, model_name: str
    ) -> pd.DataFrame:
        """Map model-specific subcategories to standard ones."""
        if model_name in self.subcategory_mappings:
            mapping = self.subcategory_mappings[model_name]
            df["Sub-Category"] = (
                df["Sub-Category"].map(mapping).fillna(df["Sub-Category"])
            )
        return df

    def _validate_against_standards(self, df: pd.DataFrame, model_name: str):
        """Validate standardized data against standards."""
        # Implementation for validation logic
        pass

    def _load_category_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load category mapping configurations."""
        return {
            "genome-sequencing-trio": {
                "Compute Costs": "Equipment",
                "Storage": "Equipment",
            },
            "panel": {"Enrichment": "Consumables"},
        }

    def _load_subcategory_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load subcategory mapping configurations."""
        return {
            "genome-sequencing-trio": {
                "AWS Compute": "Cloud Compute",
                "Local Storage": "Storage",
            }
        }
```

## Phase 3: Robustness and User Customization (4-6 weeks)

### Robustness Improvements

#### 3.1 Enhanced Error Handling

- Add comprehensive validation in `calculation_engine.py`
- Implement graceful degradation for missing data
- Add detailed logging for debugging model differences

#### 3.2 Performance Optimization

- Implement parallel processing for multi-model calculations
- Add caching for repeated computations across models
- Optimize memory usage for large datasets

#### 3.3 Data Quality Assurance

- Extend anomaly detection to cross-model validation
- Add statistical tests for cost distribution consistency
- Implement data integrity checks

### User Customization Features

#### 3.4 Configuration-Driven Customization

Extend `config.yaml` to support user customizations:

```yaml
# User customization section
user_customizations:
  lab_name: "Melbourne Genomics"
  custom_categories:
    - name: "Local Costs"
      subcategories: ["Shipping", "Local Taxes"]
  cost_adjustments:
    labor_multiplier: 1.05  # 5% adjustment for local rates
    equipment_depreciation_years: 7
```

#### 3.5 Input Template System

```python
# src/unimelb_phd_phase_1/input_templates.py
from typing import Dict, Any
import pandas as pd
from pathlib import Path


class GenomicLabTemplate:
    """Template generator for genomic lab inputs."""

    def __init__(self, lab_config: Dict[str, Any]):
        self.lab_config = lab_config
        self.required_fields = self._get_required_fields()

    def generate_excel_template(self, model_type: str) -> str:
        """Generate Excel template with standardized structure."""
        template_path = Path(f"templates/{model_type}_template.xlsx")

        # Create template with standard categories
        # Allow lab-specific customizations
        # Return path to generated template

        return str(template_path)

    def validate_user_input(self, user_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate user-provided data against standards."""
        validation_results = {"valid": True, "warnings": [], "errors": []}

        # Check for required categories
        required_cats = self.required_fields["categories"]
        user_cats = set(user_data["Category"].unique())

        missing_cats = required_cats - user_cats
        if missing_cats:
            validation_results["errors"].append(
                f"Missing required categories: {missing_cats}"
            )
            validation_results["valid"] = False

        # Check for non-standard entries
        extra_cats = user_cats - set(required_cats)
        if extra_cats:
            validation_results["warnings"].append(
                f"Non-standard categories found: {extra_cats}"
            )

        return validation_results

    def _get_required_fields(self) -> Dict[str, Any]:
        """Get required fields for validation."""
        return {
            "categories": ["Labor", "Equipment", "Consumables", "Overheads"],
            "subcategories": {
                "Labor": ["Technician", "Bioinformatician", "Scientist"],
                "Equipment": ["Sequencer", "Storage"],
                "Consumables": ["Reagents", "Libraries"],
                "Overheads": ["Facility", "Administration"],
            },
        }
```

#### 3.6 Web Interface for Customization

- Extend Flask app with configuration upload interface
- Add drag-and-drop template generation
- Implement user-guided setup wizard
- Create interactive configuration builder

#### 3.7 Plugin Architecture for Lab-Specific Logic

- Create plugin system for custom calculation rules
- Allow labs to extend formula strategies without modifying core code
- Support custom validation rules and cost calculations

## Phase 4: Testing and Validation (2-3 weeks)

### Comprehensive Test Suite

- Add tests for standardization logic
- Cross-model validation tests
- User customization scenario tests
- Performance regression tests

### Documentation and Training

- Update README with customization guide
- Create video tutorials for lab setup
- Document API for programmatic customization
- Develop troubleshooting guides

## Recommended Additional Changes

### For Increased Robustness

- **Version Control for Models**: Track changes to model configurations
- **Audit Trail**: Log all standardization transformations
- **Backup/Restore**: Ability to revert to original model structures
- **Data Integrity Checks**: Automated validation of data consistency

### For User Adoption

- **Docker Containerization**: Easy deployment for labs without Python expertise
- **API Endpoints**: REST API for integration with lab management systems
- **Sample Datasets**: Include anonymized sample data for testing
- **Cloud Deployment**: Support for AWS/Azure deployment options

### Implementation Priority

1. **High Priority**: Standardization analysis and core unification (Phases 1-2)
2. **Medium Priority**: User customization features and web interface (Phase 3)
3. **Low Priority**: Advanced plugins and Docker deployment (Phase 4+)

## Success Metrics

### Standardization Metrics

- **Category Consistency**: >90% overlap in categories across models
- **Subcategory Consistency**: >85% overlap in subcategories within categories
- **Validation Accuracy**: <5% deviation from original model results

### User Adoption Metrics

- **Template Generation**: <10 minutes to generate customized template
- **Validation Time**: <5 minutes to validate user inputs
- **Setup Time**: <30 minutes for new lab to configure system

## Risk Mitigation

### Technical Risks

- **Data Loss**: Implement backup/restore functionality
- **Performance Impact**: Monitor and optimize standardization overhead
- **Compatibility Issues**: Maintain backward compatibility with existing models

### Adoption Risks

- **Learning Curve**: Provide comprehensive documentation and training
- **Resistance to Change**: Demonstrate benefits through pilot programs
- **Support Burden**: Create self-service resources and community forums

## Timeline and Resources

### Estimated Timeline

- **Phase 1**: 1-2 weeks (Analysis and Planning)
- **Phase 2**: 2-4 weeks (Core Implementation)
- **Phase 3**: 4-6 weeks (Enhancement and Customization)
- **Phase 4**: 2-3 weeks (Testing and Documentation)
- **Total**: 9-15 weeks

### Resource Requirements

- **Development Team**: 1-2 senior developers
- **Domain Expertise**: Genomic lab specialist for validation
- **Testing**: Access to multiple genomic labs for pilot testing
- **Documentation**: Technical writer for user guides

## Conclusion

This standardization plan provides a structured approach to unify the five genomic testing models while enabling broader adoption by genomic labs worldwide. The phased implementation ensures incremental progress with validation at each step, maintaining fidelity to the original Excel models while creating a flexible, standardized framework.

The plan addresses both immediate standardization needs and long-term scalability requirements, positioning the microcosting toolkit as a comprehensive solution for genomic cost analysis research.
