# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Legacy validation command."""

from genomics_microcosting import validate_engine as _validation
from genomics_microcosting.validate_engine import validate_engine

__all__ = [name for name in vars(_validation) if not name.startswith("_")]


def __getattr__(name: str) -> object:
    """Resolve legacy validation imports from the maintained module."""
    return getattr(_validation, name)


if __name__ == "__main__":
    raise SystemExit(validate_engine())
