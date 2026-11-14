# Development Guide

This guide provides information for developers who want to contribute to the microcosting genomics analysis toolkit.

## Getting Started

### Prerequisites

- Python 3.15.1
- uv
- Git
- Gitleaks 8.30.1

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/edithatogo/microcosting_genomics.git
   cd microcosting_genomics
   ```

2. Install the package in development mode:
   ```bash
   uv sync --locked --python 3.15.1
   .venv/bin/python --version
   ```

3. Install pre-commit hooks:
   ```bash
   .venv/bin/pre-commit install
   ```

## Project Structure

See [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) for a detailed overview of the project structure.

## Development Workflow

### Code Style

Use the locked Ruff linter and formatter and the strict type checker.

```bash
.venv/bin/ruff check src
.venv/bin/ruff format --check src
.venv/bin/basedpyright
```

### Testing

Run focused tests in [tests](../tests) during edits. Run the full suite with coverage for integration.

```bash
.venv/bin/python -m pytest --disable-socket --allow-unix-socket --timeout=120 --cov=src --cov-fail-under=30 -q
```

### Pre-commit hooks

The hooks check Ruff, Git conflicts, configuration syntax and staged secrets, then run the tests selected for the changes.

```bash
.venv/bin/pre-commit run --all-files
```

## Adding New Features

### Adding New Modules

1. Create the new module in [src/genomics_microcosting/](../src/genomics_microcosting/)
2. Add corresponding tests in [tests/](../tests)
3. Update documentation in [docs/](../docs)
4. Add any necessary configuration to [config.yaml](../config.yaml)

### Adding New Scripts

1. Create the script in [scripts/](../scripts)
2. Make sure it follows the existing patterns
3. Add documentation if necessary

### Adding New Documentation

1. Create new documentation files in [docs/](../docs)
2. Update [docs/README.md](../docs/README.md) to include links to new documentation
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

1. Update [CHANGELOG.md](../CHANGELOG.md) with changes
2. Verify the package version derived from its Git tag
3. Create a new Git tag
4. Push to repository
