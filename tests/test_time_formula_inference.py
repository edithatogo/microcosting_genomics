# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check explicit, narrowly scoped workbook formula unit inference."""

import hashlib
from decimal import Decimal
lazy from pathlib import Path

import pytest
from openpyxl import Workbook

from genomics_microcosting.parameter_units import TimeConversion, TimeParameterTransform
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
)
from genomics_microcosting.scenario_comparison import verify_time_unit_sources


@pytest.mark.parametrize("fault", ["none", "formula", "link", "header", "merge", "row"])
def test_explicit_formula_inference_checks_source_chain(
    tmp_path: Path,
    fault: str,
) -> None:
    """A rate header alone cannot establish the timing formula chain."""
    book = Workbook()
    rates = book.active
    if rates is None:
        raise AssertionError
    rates.title = "rates"
    if fault != "merge":
        rates.merge_cells("AB1:AD1")
    rates["AB1"] = "wrong" if fault == "header" else "Base Salary + Costs (hourly)"
    timing = book.create_sheet("timing")
    for cost, rate, source in (("AA", "K", "AB"), ("AB", "L", "AC"), ("AC", "M", "AD")):
        timing[f"{cost}5"] = f"=$G5/60*{rate}5"
        timing[f"{rate}5"] = f"='rates'!{source}$4"
    if fault == "formula":
        timing["AA5"] = "=$G5/100*K5"
    if fault == "link":
        timing["K5"] = "='rates'!AC$4"
    path = tmp_path / "source.xlsx"
    book.save(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    location = "WB02:G6" if fault == "row" else "WB02:G5"
    source = SourceRecord(
        source_id="source",
        sha256=digest,
        edition="synthetic",
        locator=location,
        limitations="Synthetic formula inference",
    )
    parameter = Parameter(
        parameter_id="time",
        raw_value="90",
        derived_value="1.5",
        unit="h",
        source_sha256=digest,
        source_locator=location,
        transformation="minutes / 60",
        uncertainty="unmeasured",
        status="derived",
    )
    qualification = ParameterQualification(
        parameter=parameter,
        source=source,
        exact_support="synthetic",
        dimensional_basis="time",
        applicability="synthetic",
        qualification="unresolved",
        blockers=("inferred unit",),
    )
    ledger = QualificationLedger(
        parameter_set=ParameterSet(
            version_id="v1",
            workbook_sha256=digest,
            parameters=(parameter,),
        ),
        qualifications=(qualification,),
    )
    transform = TimeParameterTransform(
        parameter=parameter,
        conversion=TimeConversion(
            raw_value=Decimal(90),
            source_unit="min",
            target_unit="h",
            source=source,
            unit_locator="WB02:AA5:AC5; WB01:AB1 hourly salary header",
            unit_basis="workbook_formula_inference",
        ),
        rounding_policy="exact",
    )
    if fault == "none":
        verify_time_unit_sources(ledger, (transform,), {"source": path})
    else:
        with pytest.raises(ValueError, match=r"inference|header"):
            verify_time_unit_sources(ledger, (transform,), {"source": path})
