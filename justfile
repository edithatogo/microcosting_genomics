# A simple command runner for a new project.

# Install dependencies
install:
    pip install -e .[dev]

# Run the main application
run:
    @echo "No run command configured."

# Run tests
test:
    pytest

# Run property-based tests
test-property:
    pytest --hypothesis-profile=dev

# Lint the code
lint:
    pre-commit run --all-files

# Format the code
format:
    ruff format .
    isort .
    black .

# Run security checks
security:
    bandit -c pyproject.toml -r .
