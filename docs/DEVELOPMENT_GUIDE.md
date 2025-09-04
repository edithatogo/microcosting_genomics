# Development Guide

This guide provides information for developers who want to contribute to the microcosting genomics analysis toolkit.

## Getting Started

### Prerequisites

- Python 3.8 or later
- pip package manager
- Git version control

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/microcosting_genomics.git
   cd microcosting_genomics
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .[dev]
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Project Structure

See [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) for a detailed overview of the project structure.

## Development Workflow

### Code Style

This project follows the PEP 8 style guide. Code formatting is handled by Black and import sorting by isort.

- Run `black .` to format code
- Run `isort .` to sort imports
- Run `ruff check .` to check for linting issues

### Testing

The project uses pytest for testing. All tests are located in the [tests/](file:///Users/doughnut/GitHub/microcosting_genomics/tests) directory.

To run all tests:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=src/unimelb_phd_phase_1
```

### Pre-commit Hooks

Pre-commit hooks are configured to run automatically before each commit. They include:
- Black for code formatting
- isort for import sorting
- ruff for linting
- bandit for security checks

To run all hooks manually:
```bash
pre-commit run --all-files
```

## Adding New Features

### Adding New Modules

1. Create the new module in [src/unimelb_phd_phase_1/](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/)
2. Add corresponding tests in [tests/](file:///Users/doughnut/GitHub/microcosting_genomics/tests)
3. Update documentation in [docs/](file:///Users/doughnut/GitHub/microcosting_genomics/docs)
4. Add any necessary configuration to [config.yaml](file:///Users/doughnut/GitHub/microcosting_genomics/config.yaml)

### Adding New Scripts

1. Create the script in [scripts/](file:///Users/doughnut/GitHub/microcosting_genomics/scripts)
2. Make sure it follows the existing patterns
3. Add documentation if necessary

### Adding New Documentation

1. Create new documentation files in [docs/](file:///Users/doughnut/GitHub/microcosting_genomics/docs)
2. Update [docs/README.md](file:///Users/doughnut/GitHub/microcosting_genomics/docs/README.md) to include links to new documentation
3. Ensure documentation follows the existing format

## API Documentation

Each module should have comprehensive docstrings that explain:
- Module purpose
- Class and function descriptions
- Parameter and return value documentation
- Usage examples

## Contributing

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Make your changes
4. Add tests for your changes
5. Update documentation as needed
6. Run the test suite to ensure everything works
7. Submit a pull request

## Release Process

1. Update [CHANGELOG.md](file:///Users/doughnut/GitHub/microcosting_genomics/CHANGELOG.md) with changes
2. Update version in [pyproject.toml](file:///Users/doughnut/GitHub/microcosting_genomics/pyproject.toml) and [src/unimelb_phd_phase_1/__init__.py](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/__init__.py)
3. Create a new Git tag
4. Push to repository