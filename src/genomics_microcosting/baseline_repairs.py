# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Build diagnostic formula overlays without modifying workbook baselines."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

SOURCE_SHA256 = "2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4"


def diagnostic_overlay(
    formulas: Mapping[tuple[str, str], str],
    changes: Sequence[tuple[str, str, str, str]],
    *,
    source_sha256: str,
    diagnostic_opt_in: bool = False,
) -> dict[tuple[str, str], str]:
    """Return an isolated overlay after checking every source precondition.

    Args:
        formulas: Formula map extracted from the hashed source workbook.
        changes: Sheet, cell, original formula and proposed formula records.
        source_sha256: SHA-256 of the workbook used to extract formulas.
        diagnostic_opt_in: Explicit acknowledgement of diagnostic scope.

    Returns:
        A new formula map; no recalculation or scientific adoption is implied.

    Raises:
        ValueError: Selection, source identity or formula preconditions fail.

    """
    if not diagnostic_opt_in:
        msg = "Diagnostic corrections require explicit opt-in"
        raise ValueError(msg)
    if source_sha256 != SOURCE_SHA256:
        msg = "Workbook source identity does not match the repair edition"
        raise ValueError(msg)
    if not changes:
        msg = "Select at least one diagnostic formula change"
        raise ValueError(msg)
    selected: dict[tuple[str, str], str] = {}
    for sheet, cell, original, proposed in changes:
        key = (sheet, cell)
        if key in selected:
            msg = "Duplicate diagnostic target"
            raise ValueError(msg)
        if formulas.get(key) != original:
            msg = "Original formula precondition failed"
            raise ValueError(msg)
        if not proposed.startswith("=") or proposed == original:
            msg = "Diagnostic replacement must be a changed formula"
            raise ValueError(msg)
        selected[key] = proposed
    return dict(formulas) | selected
