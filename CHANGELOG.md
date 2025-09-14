# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-09-14
### Changed
- **Package Name Standardization**: Renamed all references from `unimelb_phd_phase_1` to `genomics_microcosting` across the entire codebase
- **Import Updates**: Updated all Python import statements to use the correct package name
- **Documentation Updates**: Updated README, Copilot instructions, and all documentation files
- **CI/CD Updates**: Updated GitHub Actions workflow to use correct package paths
- **Test Suite Updates**: Updated all test files with correct imports and patch decorators

### Fixed
- Import errors caused by inconsistent package naming
- Documentation references to old package name

## [2025-07-27]
### Changed
- Tests now run without installing the package by modifying import paths.
- All files have proper trailing newlines and formatted style.
- Removed legacy package variant and obsolete calculation engine code.
