# Genomics Microcosting Refactoring Plan

## Comprehensive Naming Convention Review & System Modernization

**Date:** 14 September 2025
**Repository:** microcosting_genomics
**Current Status:** Analysis Complete, Ready for Phase 1 Implementation

---

## 📋 Executive Summary

This document outlines a comprehensive refactoring plan to modernize the genomics microcosting codebase by:

- Removing PhD-specific naming conventions
- Implementing systematic naming standards
- Abstracting cost components for better maintainability
- Enhancing the microcosting model's compute and storage cost components
- Future-proofing for additional genomics cost factors

**Total Estimated Effort:** 12-16 weeks
**Risk Level:** Medium (incremental changes with validation at each step)
**Business Impact:** High (improves code maintainability, extensibility, and professional standards)

---

## 🎯 Project Objectives

### Primary Goals

1. **Professional Naming**: Remove PhD-specific references and implement industry-standard naming
2. **Modular Architecture**: Separate concerns and create reusable components
3. **Enhanced Cost Modeling**: Improve compute and storage cost components within the microcosting model
4. **Future-Proofing**: Design for extensibility with additional genomics cost factors

### Success Criteria

- ✅ All PhD references removed from package names and documentation
- ✅ Consistent naming conventions across all code and data structures
- ✅ Modular cost component system with clear separation of concerns
- ✅ Enhanced microcosting model with detailed compute/storage breakdown
- ✅ Comprehensive test coverage for all new components
- ✅ Validation that refactored system produces identical results to current system

---

## 📊 Current State Analysis

### Codebase Overview

- **Language:** Python 3.8+
- **Primary Package:** `unimelb_phd_phase_1` (needs renaming)
- **Key Components:** Calculation engine, formula parser, strategy pattern implementations
- **Data Sources:** Excel workbooks with complex multi-level headers
- **Test Coverage:** 93 tests passing, comprehensive validation framework

### Naming Convention Issues Identified

1. **PhD Context**: Package name `unimelb_phd_phase_1` is too specific
2. **Abbreviations**: DSA, VCGS not immediately clear to new developers
3. **Inconsistent Terms**: Mix of full terms and abbreviations in column names
4. **Model References**: Hardcoded model logic without clear taxonomy

### Architecture Assessment

- **Strengths:** Well-implemented strategy pattern, comprehensive formula parsing
- **Opportunities:** Cost component abstraction, modular data pipeline, enhanced microcosting details

---

## 🗂️ Detailed Implementation Plan

### Phase 1: Naming Standardization (Weeks 1-2)

**Goal:** Establish consistent, professional naming conventions

#### 1A: Package Renaming

- **Task:** Rename `src/unimelb_phd_phase_1/` to `src/genomics_microcosting/`
- **Files to Update:** All Python files with imports, setup.py, pyproject.toml
- **Risk:** Import errors - validate all imports after changes
- **Testing:** Run full test suite after each import update

#### 1B: Column Naming Standardization

- **Task:** Create standardized column taxonomy in config.yaml
- **Implementation:** Define clear mappings for all data columns

```yaml
column_mapping:
  test_id: "Test"
  category: "Category"
  total_cost: "Total Cost"
  sequencing_type: "Sequencing Type"
```

#### 1C: Abbreviation Standardization

- **Task:** Replace unclear abbreviations with descriptive terms
- **Mappings:**
  - DSA → Deterministic Sensitivity Analysis
  - VCGS → Victorian Clinical Genetics Services
  - WES/WGS → Whole Exome/Genome Sequencing (keep as standard)

#### 1D: Model Reference Standardization

- **Task:** Create GenomicsModel enum and update all references
- **Implementation:** Replace hardcoded strings with enum values

### Phase 2: Cost Component Abstraction (Weeks 3-4)

**Goal:** Create reusable, modular cost component system

#### 2A: Base Classes

- **Task:** Create `cost_components.py` with base CostComponent class
- **Implementation:** Abstract base class with common cost calculation methods

#### 2B: Genomics-Specific Components

- **Task:** Implement StorageCostComponent and ComputeCostComponent
- **Focus:** Detailed breakdown for genomics microcosting model
- **Storage Components:** Raw sequences, aligned data, variants, archives
- **Compute Components:** Alignment, variant calling, annotation, QC

#### 2C: Allocation Logic

- **Task:** Implement GenomicsCostAllocator for dynamic cost allocation
- **Use Cases:** Different allocation by test type (WES vs WGS) and sample volume

### Phase 3: Model Configuration System (Weeks 5-6)

**Goal:** Make model definitions configurable instead of hardcoded

#### 3A: YAML Configuration Structure

- **Task:** Create `config/models.yaml` with structured model definitions
- **Include:** Cost factors, efficiency multipliers, resource requirements

#### 3B: Configuration Loader

- **Task:** Implement ModelConfigLoader class with validation
- **Features:** Schema validation, error handling, default fallbacks

#### 3C: Engine Integration

- **Task:** Update CalculationEngine to use configuration system
- **Migration:** Replace hardcoded logic with configurable parameters

### Phase 4: Data Pipeline Modularization (Weeks 7-8)

**Goal:** Create flexible, extensible data processing pipeline

#### 4A: Pipeline Architecture

- **Task:** Create DataPipeline class with modular components
- **Pattern:** Extractor → Transformer → Loader pattern

#### 4B: Extractor Components

- **Task:** Implement ExcelExtractor, CSVExtractor, APIExtractor
- **Goal:** Support multiple data source types

#### 4C: Transformer Components

- **Task:** Implement HeaderNormalizer, CostCalculator, ValidationChecker
- **Goal:** Modular data transformation steps

#### 4D: Migration

- **Task:** Refactor prepare_data.py to use new pipeline
- **Validation:** Ensure identical output to current system

### Phase 5: Enhanced Microcosting Components (Weeks 9-10)

**Goal:** Improve compute and storage cost modeling within microcosting

#### 5A: Storage Cost Enhancement

- **Task:** Add detailed storage breakdown to microcosting model
- **Components:** Raw data, processed data, archive data, retention policies

#### 5B: Compute Cost Enhancement

- **Task:** Add bioinformatics-specific compute breakdown
- **Components:** Sequencing, alignment, variant calling, annotation, QC

#### 5C: Scaling Factors

- **Task:** Implement volume-based cost scaling
- **Features:** Batch processing efficiencies, volume discounts

### Phase 6: Future-Proofing (Weeks 11-12)

**Goal:** Design for extensibility and additional cost factors

#### 6A: Extensible Input Schema

- **Task:** Design schema for future genomics cost factors
- **Considerations:** New sequencing technologies, cloud costs, regulatory changes

#### 6B: API Integration

- **Task:** Add interfaces for external data sources
- **Use Cases:** Real-time pricing, external cost databases

#### 6C: Advanced Algorithms

- **Task:** Implement sophisticated cost allocation algorithms
- **Features:** Machine learning-based cost prediction, scenario analysis

### Phase 7: Documentation Updates (Week 13)

**Goal:** Update all documentation to reflect new structure

**Tasks:**

- Update README.md with new package structure
- Update docstrings for all classes and methods
- Create API documentation for new components
- Update installation and usage instructions

### Phase 8: Testing & Validation (Week 14)

**Goal:** Ensure system reliability and backward compatibility

**Tasks:**

- Create comprehensive test suite for new components
- Validate against existing microcosting results
- Performance testing for new architecture
- Integration testing across all components

### Phase 9: CI/CD Updates (Week 15)

**Goal:** Update deployment and testing infrastructure

**Tasks:**

- Update CI pipeline for new package structure
- Add test coverage requirements
- Update deployment scripts
- Configure monitoring for new components

---

## 🔧 Implementation Guidelines

### Code Standards

- **Naming:** Use descriptive names, avoid abbreviations unless industry-standard
- **Structure:** Follow existing patterns (strategy pattern, modular design)
- **Documentation:** Comprehensive docstrings for all new classes/methods
- **Testing:** Unit tests for all new components, integration tests for workflows

### Risk Mitigation

- **Incremental Changes:** Each phase can be implemented independently
- **Backward Compatibility:** Maintain existing API until migration complete
- **Validation:** Run full test suite after each major change
- **Rollback Plan:** Git branches for each phase, easy reversion if needed

### Dependencies

- **Phase Dependencies:** Later phases depend on earlier ones
- **Parallel Work:** Some tasks within phases can be done in parallel
- **Testing Dependencies:** All changes require validation against existing results

### Success Metrics

- **Code Quality:** 100% test coverage for new components
- **Performance:** No degradation in calculation speed
- **Maintainability:** Clear separation of concerns, modular architecture
- **Extensibility:** Easy addition of new cost components and models

---

## 📈 Progress Tracking

### Current Status

- ✅ **Phase 0:** Analysis Complete
- 🔄 **Phase 1:** Ready to start (Naming Standardization)

### Weekly Milestones

- **Week 2:** Phase 1 Complete - Consistent naming throughout codebase
- **Week 4:** Phase 2 Complete - Modular cost component system
- **Week 6:** Phase 3 Complete - Configurable model system
- **Week 8:** Phase 4 Complete - Modular data pipeline
- **Week 10:** Phase 5 Complete - Enhanced microcosting components
- **Week 12:** Phase 6 Complete - Future-proofed architecture
- **Week 15:** All phases complete, fully tested and documented

### Monitoring

- Daily: Run test suite to ensure no regressions
- Weekly: Code review of completed work
- Phase End: Full validation against existing microcosting results

---

## 🚀 Getting Started

### Prerequisites

1. Full test suite passing on current codebase
2. Backup of current working system
3. Git branch created for refactoring work
4. Documentation of current system behavior

### First Steps

1. Create feature branch: `git checkout -b genomics-refactoring`
2. Run baseline validation: `python validate_engine.py`
3. Begin Phase 1A: Package renaming
4. Update imports incrementally, testing after each change

### Emergency Rollback

```bash
# If issues arise, rollback to baseline
git checkout main
git branch -D genomics-refactoring
```

---

## 📞 Support & Communication

### Key Contacts

- **Technical Lead:** [Current maintainer]
- **Domain Expert:** [Genomics microcosting specialist]

### Communication Plan

- **Daily Standups:** Quick progress updates
- **Weekly Reviews:** Detailed phase completion assessment
- **Issues:** Immediate escalation for blocking problems

### Documentation Updates

- This document will be updated weekly with progress
- All changes documented in CHANGELOG.md
- Code changes include comprehensive commit messages

---

**This plan provides a robust, incremental approach to modernizing the genomics microcosting codebase while maintaining system reliability and enabling future enhancements.**
