# Contribution Guidelines

Welcome to the Genomics Microcosting Project! We're excited that you're interested in contributing to our open-source project. This document outlines the process and guidelines for contributing to the project.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Style and Standards](#code-style-and-standards)
4. [Testing Guidelines](#testing-guidelines)
5. [Documentation Standards](#documentation-standards)
6. [Pull Request Process](#pull-request-process)
7. [Reporting Issues](#reporting-issues)
8. [Community Guidelines](#community-guidelines)

## Getting Started

### Prerequisites

- Python 3.15.1
- uv
- Git
- Gitleaks 8.30.1

### Setting Up Development Environment

1. Fork the repository on GitHub
2. Clone your forked repository:
   ```bash
   git clone https://github.com/your-username/microcosting_genomics.git
   cd microcosting_genomics
   ```

3. Create the repository environment and install locked dependencies.
   ```bash
   uv sync --locked --python 3.15.1
   .venv/bin/python --version
   ```

4. Install pre-commit hooks.
   ```bash
   .venv/bin/pre-commit install
   ```

5. Verify the installation with the test suite.
   ```bash
   .venv/bin/python -m pytest
   ```

## Development Workflow

### Branching Strategy
We follow the GitFlow branching model:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature branches
- `hotfix/*`: Bug fix branches
- `release/*`: Release preparation branches

### Creating a Feature Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Making Changes
1. Write code following our style guidelines
2. Add or update unit tests
3. Update documentation as needed
4. Run all tests to ensure nothing is broken
5. Commit changes with clear, descriptive messages

### Commit Message Guidelines
Follow the conventional commit format:
```
type(scope): brief description

Detailed explanation of the changes (optional)

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(calculation): add support for SUMPRODUCT formulas

Implement the SUMPRODUCT calculation strategy to handle Excel SUMPRODUCT functions.
This enables more complex cost calculations in the analysis.

Fixes #45
```

## Code Style and Standards

### Python Style Guide
We follow PEP 8 with some additional conventions:

1. **Line Length**: Maximum 88 characters (compatible with Black formatter)
2. **Naming Conventions**:
   - Classes: `PascalCase`
   - Functions and variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private members: prefixed with `_`

3. **Imports**:
   - Group imports in order: standard library, third-party, local
   - Use absolute imports when possible
   - Avoid wildcard imports

4. **Type Hints**:
   - Use type hints for function parameters and return values
   - Import typing modules only as needed

Example:
```python
from typing import Dict, List, Optional


def calculate_total_cost(
    unit_costs: List[float],
    quantities: List[int],
    discount_rate: Optional[float] = None,
) -> float:
    """Calculate total cost with optional discount.

    Args:
        unit_costs: List of unit costs
        quantities: List of quantities
        discount_rate: Optional discount rate (0.0 to 1.0)

    Returns:
        Total cost after discount
    """
    subtotal = sum(cost * qty for cost, qty in zip(unit_costs, quantities))

    if discount_rate is not None:
        return subtotal * (1 - discount_rate)
    return subtotal
```

### Code Quality Tools
We use several tools to maintain code quality:

1. **Black**: Code formatter
2. **Ruff**: Linter and code quality checker
3. **isort**: Import sorter
4. **Bandit**: Security vulnerability scanner

Run these tools before committing:
```bash
black src/
ruff check src/
isort src/
bandit -r src/
```

### Error Handling
1. Use specific exception types rather than generic exceptions
2. Provide meaningful error messages
3. Log errors appropriately
4. Implement graceful degradation where possible

### Security Considerations
1. Sanitize all user inputs
2. Validate file paths to prevent directory traversal
3. Use secure configuration storage for sensitive data
4. Implement proper access controls

## Testing Guidelines

### Test Structure
We use pytest for testing with the following structure:

```
tests/
├── test_module_name.py
└── conftest.py  # Shared test fixtures
```

### Writing Tests
1. **Test File Naming**: `test_*.py` or `*_test.py`
2. **Test Function Naming**: `test_*`
3. **Use Descriptive Names**: Clearly indicate what is being tested
4. **Follow AAA Pattern**: Arrange, Act, Assert

Example:
```python
import pytest
import pandas as pd
from unimelb_phd_phase_1.calculation_engine import CalculationEngine


class TestCalculationEngine:
    """Test cases for CalculationEngine."""

    def test_execute_simple_multiplication(self):
        """Test executing a simple multiplication formula."""
        # Arrange
        engine = CalculationEngine(MockSheetManager())
        formula = {"type": "multiplication", "operands": [2, 3]}

        # Act
        result = engine.execute_formula(formula, "TestSheet", "A1")

        # Assert
        assert result == 6
```

### Test Coverage
1. **Target**: 90%+ test coverage for new code
2. **Types**: Unit tests, integration tests, and end-to-end tests
3. **Edge Cases**: Test boundary conditions and error cases
4. **Data Quality**: Test with various data formats and sizes

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_module.py

# Run with coverage report
python -m pytest --cov=src/

# Run tests in parallel
python -m pytest -n auto
```

## Documentation Standards

### Code Documentation
1. **Docstrings**: Use Google-style docstrings for all public functions and classes
2. **Inline Comments**: Explain why, not what
3. **Type Hints**: Document parameter and return types

### User Documentation
1. **README.md**: Keep up-to-date with installation and usage instructions
2. **API Reference**: Document all public APIs
3. **Tutorials**: Provide step-by-step guides for common workflows
4. **Troubleshooting**: Document common issues and solutions

### Documentation Format
We use Markdown for documentation with the following conventions:

1. **Headers**: Use proper header hierarchy (#, ##, ###)
2. **Code Blocks**: Specify language for syntax highlighting
3. **Links**: Use relative links for internal documentation
4. **Lists**: Use consistent formatting for ordered and unordered lists

## Pull Request Process

### Before Submitting
1. Ensure all tests pass
2. Update documentation as needed
3. Follow code style guidelines
4. Write clear, descriptive commit messages
5. Rebase on latest develop branch

### Pull Request Template
When creating a pull request, include:

1. **Description**: Clear explanation of changes
2. **Related Issues**: Link to any related GitHub issues
3. **Testing**: Description of how changes were tested
4. **Breaking Changes**: Note any breaking changes
5. **Screenshots**: If applicable, include screenshots

### Review Process
1. Automated checks must pass
2. At least one code review required
3. Address all review comments
4. Squash fixup commits before merge

### Merging
1. Use squash and merge for feature branches
2. Write a clear merge commit message
3. Delete feature branch after merging

## Reporting Issues

### Before Creating an Issue
1. Search existing issues
2. Check documentation
3. Try latest development version

### Issue Template
When creating an issue, include:

1. **Description**: Clear, concise description of the problem
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, package versions
6. **Additional Context**: Any other relevant information

### Issue Labels
We use labels to categorize issues:
- `bug`: Confirmed bugs
- `enhancement`: Feature requests
- `documentation`: Documentation issues
- `help wanted`: Good issues for new contributors
- `good first issue`: Issues suitable for beginners

## Community Guidelines

### Code of Conduct
We follow the Contributor Covenant Code of Conduct. By participating in this project, you agree to abide by its terms.

### Communication
1. **Be Respectful**: Treat all contributors with respect
2. **Be Constructive**: Provide helpful feedback
3. **Be Inclusive**: Welcome diverse perspectives
4. **Be Professional**: Maintain professional standards

### Getting Help
1. **GitHub Issues**: For bug reports and feature requests
2. **Documentation**: Check existing documentation first
3. **Community**: Engage with the community on discussion forums

### Recognition
We value all contributions, including:
- Code contributions
- Documentation improvements
- Bug reports
- Feature requests
- Community support

Contributors will be acknowledged in:
- Release notes
- Contributor list
- Project documentation

## Release Process

### Versioning
We follow Semantic Versioning (SemVer):
- MAJOR version for incompatible API changes
- MINOR version for backward-compatible functionality
- PATCH version for backward-compatible bug fixes

### Release Checklist
Before creating a release:
1. Update version number in [pyproject.toml](file:///Users/doughnut/GitHub/microcosting_genomics/pyproject.toml)
2. Update CHANGELOG.md
3. Ensure all tests pass
4. Create release branch
5. Create GitHub release with release notes

## Additional Resources

### Development Tools
- **IDE**: VS Code with Python extensions recommended
- **Debugging**: Use pytest with --pdb flag for interactive debugging
- **Profiling**: Use built-in profiling tools for performance optimization

### Learning Resources
- [Python Documentation](https://docs.python.org/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)

### Project-Specific Resources
- [API Reference](file:///Users/doughnut/GitHub/microcosting_genomics/docs/API_REFERENCE.md)
- [Development Guide](file:///Users/doughnut/GitHub/microcosting_genomics/docs/DEVELOPMENT_GUIDE.md)
- [Architecture Documentation](file:///Users/doughnut/GitHub/microcosting_genomics/docs/REPOSITORY_STRUCTURE.md)

Thank you for contributing to the Genomics Microcosting Project! Your contributions help make this tool better for researchers and analysts in the genomics field.
