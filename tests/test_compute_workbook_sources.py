# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Bind T5 numeric observations to an exact baseline workbook snapshot."""

import re
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
lazy from pathlib import Path

import pytest
from openpyxl import Workbook

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    ComputePricing,
    calculate_compute_cost,
)
from tests import checks
from tests.test_compute_cost import inputs


def workbook_inputs(
    tmp_path: Path,
    *,
    value: float | str | bool | None = 10,
    locator: str = "WB01:A1",
    cache: str | None = None,
) -> tuple[ComputePricing, ComputeCostContext]:
    """Replace one synthetic observation with a registered workbook cell."""
    pricing, context = inputs(tmp_path)
    path = tmp_path / "baseline.xlsx"
    book = Workbook()
    book["Sheet"]["A1"] = value
    book.save(path)
    book.close()
    if cache is not None:
        with ZipFile(BytesIO(path.read_bytes())) as incoming, ZipFile(path, "w") as out:
            for member in incoming.infolist():
                payload = incoming.read(member)
                if member.filename == "xl/worksheets/sheet1.xml":
                    payload, count = re.subn(
                        rb"<v(?:\s*/>|></v>)",
                        f"<v>{cache}</v>".encode(),
                        payload,
                    )
                    if count != 1:
                        raise AssertionError
                out.writestr(member, payload)
    digest = sha256(path.read_bytes()).hexdigest()
    q = context.ledger.qualifications[0]
    source = q.source.model_copy(update={"sha256": digest, "locator": locator})
    parameter = q.parameter.model_copy(
        update={
            "source_sha256": digest,
            "source_locator": locator,
        },
    )
    ledger = context.ledger.model_copy(
        update={
            "parameter_set": context.ledger.parameter_set.model_copy(
                update={
                    "workbook_sha256": digest,
                    "parameters": (
                        parameter,
                        *context.ledger.parameter_set.parameters[1:],
                    ),
                },
            ),
            "qualifications": (
                q.model_copy(update={"source": source, "parameter": parameter}),
                *context.ledger.qualifications[1:],
            ),
        },
    )
    snapshots = {**context.snapshots, "quantity": path}
    validity = (
        context.validity[0].model_copy(update={"source": source}),
        *context.validity[1:],
    )
    return pricing, replace(
        context,
        ledger=ledger,
        snapshots=snapshots,
        validity=validity,
    )


def test_baseline_workbook_observation_matches_exact_cell(tmp_path: Path) -> None:
    """Numeric readback uses registered bytes; tampering does not retain acceptance."""
    pricing, context = workbook_inputs(tmp_path)
    result = calculate_compute_cost(pricing, context)
    checks.require_equal(result.modeled_total, Decimal(20))
    checks.require_equal(result.allocated_cost, Decimal(10))
    path = context.snapshots["quantity"]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="hash"):
        calculate_compute_cost(pricing, context)


@pytest.mark.parametrize("value", [True, "10", None, "=5+5", "#N/A", 11])
def test_missing_or_nonnumeric_workbook_observations_are_rejected(
    tmp_path: Path,
    *,
    value: int | str | bool | None,
) -> None:
    """A missing formula cache, error, text, boolean or mismatched number fails."""
    pricing, context = workbook_inputs(tmp_path, value=value)
    with pytest.raises((ValueError, TypeError), match=r"numeric|differs"):
        calculate_compute_cost(pricing, context)


@pytest.mark.parametrize("locator", ["WB00:A1", "WB02:A1", "WB01:A1:A2", "line 1"])
def test_workbook_locators_cannot_change_source_scope(
    tmp_path: Path,
    locator: str,
) -> None:
    """Workbook identity requires one exact supported cell location."""
    pricing, context = workbook_inputs(tmp_path, locator=locator)
    with pytest.raises(ValueError, match="locator"):
        calculate_compute_cost(pricing, context)


def test_formula_cache_observation_is_not_independent_calculation(
    tmp_path: Path,
) -> None:
    """Read the cache without claiming its formula was independently evaluated."""
    pricing, context = workbook_inputs(tmp_path, value="=5+6", cache="10")
    checks.require_equal(
        calculate_compute_cost(pricing, context).modeled_total,
        Decimal(20),
    )
    foreign = replace(
        context,
        ledger=context.ledger.model_copy(
            update={
                "parameter_set": context.ledger.parameter_set.model_copy(
                    update={
                        "workbook_sha256": "f" * 64,
                    },
                ),
            },
        ),
    )
    with pytest.raises(ValueError, match="UTF-8"):
        calculate_compute_cost(pricing, foreign)
