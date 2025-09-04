# Contributing to Microcosting Genomics Analysis Toolkit

Thank you for your interest in contributing to the Microcosting Genomics Analysis Toolkit! This document provides guidelines for contributing to the project.

## How to Contribute

There are many ways to contribute to this project:

1. Report bugs and issues
2. Suggest new features
3. Improve documentation
4. Write code patches
5. Review pull requests

## Reporting Issues

Before reporting an issue, please check if it has already been reported. If not, create a new issue with:

- A clear and descriptive title
- A detailed description of the problem
- Steps to reproduce the issue
- Expected vs. actual behavior
- Any relevant error messages or logs
- Information about your environment (OS, Python version, etc.)

## Feature Requests

To suggest a new feature:

1. Check if the feature has already been requested
2. Create a new issue with a clear title and detailed description
3. Explain why the feature would be useful
4. Provide examples of how the feature would be used

## Code Contributions

### Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/microcosting_genomics.git
   cd microcosting_genomics
   ```
3. Install the package in development mode:
   ```bash
   pip install -e .[dev]
   ```
4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Making Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Add tests for your changes
4. Update documentation as needed
5. Run the test suite:
   ```bash
   pytest
   ```
6. Run pre-commit hooks:
   ```bash
   pre-commit run --all-files
   ```

### Code Style

This project follows the PEP 8 style guide. Code formatting is handled by Black and import sorting by isort.

- Run `black .` to format code
- Run `isort .` to sort imports
- Run `ruff check .` to check for linting issues

### Testing

All contributions must include appropriate tests. The project uses pytest for testing.

- Place unit tests in the [tests/](file:///Users/doughnut/GitHub/microcosting_genomics/tests) directory
- Follow the existing naming conventions (`test_*.py`)
- Ensure all tests pass before submitting a pull request
- Write clear, descriptive test names
- Include edge cases in your tests

### Documentation

Keep documentation up to date with your changes:

- Update docstrings in the code
- Update relevant documentation files in [docs/](file:///Users/doughnut/GitHub/microcosting_genomics/docs)
- Add new documentation files when adding new modules
- Ensure all public APIs are documented

### Pull Requests

When you're ready to submit your changes:

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Create a pull request from your fork to the main repository
3. Provide a clear title and description for your pull request
4. Link to any related issues
5. Request review from maintainers

### Pull Request Guidelines

- Keep pull requests focused on a single feature or bug fix
- Write clear, descriptive commit messages
- Include tests for new functionality
- Update documentation as needed
- Ensure all tests pass
- Address any feedback from reviewers promptly

## Development Workflow

See [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) for detailed information about the development workflow.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Be respectful and inclusive in all interactions.

## Questions?

If you have any questions about contributing, feel free to:

1. Open an issue for discussion
2. Contact the maintainers directly

Thank you for contributing to the Microcosting Genomics Analysis Toolkit!