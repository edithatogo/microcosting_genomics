"""Test package setup."""

# Ensure the repository root is on sys.path when the package is not installed
try:
    import unimelb_phd_phase_1  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - only executed in CI without install
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
