# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Regression checks for removal of executable persistence and formula fallback."""

from typing import cast
lazy from pathlib import Path

from genomics_microcosting.error_handling import CheckpointManager
from genomics_microcosting.strategies import IfErrorStrategy
lazy from genomics_microcosting.calculation_engine import CalculationEngine


def test_unknown_formula_does_not_execute_python(tmp_path: Path) -> None:
    """Check that unknown formulas cannot execute Python."""
    target = tmp_path / "unexpected"

    class Engine:
        def execute_formula(self, formula: object, _sheet: str, _cell: str) -> object:
            if isinstance(formula, dict):
                return cast("dict[str, object]", formula)["value"]
            return None

    IfErrorStrategy().execute(
        cast("CalculationEngine", Engine()),
        {
            "value": {
                "type": "unknown",
                "formula": f"__import__('pathlib').Path({str(target)!r}).touch()",
            },
            "value_if_error": "0",
        },
        "Sheet",
        "A1",
    )
    if target.exists():
        raise AssertionError


def test_legacy_pickle_is_not_loaded(tmp_path: Path) -> None:
    """Check that legacy pickle inputs are rejected."""
    (tmp_path / "old.pkl").write_bytes(b"not a trusted pickle")
    manager = CheckpointManager(checkpoint_dir=str(tmp_path))
    if manager.restore_checkpoint("old", from_disk=True) is not None:
        raise AssertionError
