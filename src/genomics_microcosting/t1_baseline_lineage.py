# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Known static dependencies of the preserved 2023 baseline workbook.

The index covers three identified zero-unit-cost inputs only. It is not a
complete inventory of assumptions or a proof of dynamic/external dependencies.
"""

import json
from functools import cache
from hashlib import sha256
from importlib.resources import files
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from typing import TypedDict

    class LineageIndex(TypedDict):
        """Serialized, source-bound static dependency index."""

        workbook_sha256: str
        required_by_cell: dict[str, list[str]]


BASELINE_SHA256 = "2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4"
INDEX_SHA256 = "c9c7b042ce024af28307be2d080f97f256933392d05c846cef0af2bad0222e54"


@cache
def _known_index() -> LineageIndex:
    """Read the immutable index and fail if package data is absent or altered."""
    payload = (
        files("genomics_microcosting")
        .joinpath("data", "t1_known_zero_lineage.json")
        .read_bytes()
    )
    if sha256(payload).hexdigest() != INDEX_SHA256:
        msg = "Known baseline dependency index has changed"
        raise ValueError(msg)
    index = cast("LineageIndex", json.loads(payload))
    if index["workbook_sha256"] != BASELINE_SHA256:
        msg = "Known baseline dependency source identity mismatch"
        raise ValueError(msg)
    return index


def require_known_baseline_scope(
    workbook_sha256: str,
    baseline_locator: str,
    required_parameter_ids: tuple[str, ...],
) -> None:
    """Reject a declared scope that omits known dependencies of a source cell."""
    if workbook_sha256 != BASELINE_SHA256:
        return
    required = set(_known_index()["required_by_cell"].get(baseline_locator, ()))
    if not required <= set(required_parameter_ids):
        missing = ", ".join(sorted(required - set(required_parameter_ids)))
        msg = f"Baseline scope omits known unresolved inputs: {missing}"
        raise ValueError(msg)
