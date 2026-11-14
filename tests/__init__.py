# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test package setup."""

# Ensure the repository root is on sys.path when the package is not installed
from importlib import import_module

try:
    import_module("genomics_microcosting")
except ModuleNotFoundError:  # pragma: no cover - only executed in CI without install
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    sys.path.insert(0, str(src_path))
    sys.path.insert(0, str(repo_root))
