# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Uncertainty records retain provenance without inventing a distribution."""

from decimal import Decimal
from hashlib import sha256
lazy from pathlib import Path

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterSet,
    SourceRecord,
)
from genomics_microcosting.uncertainty_provenance import (
    BoundValue,
    EvidenceDeclaration,
    UncertaintyLedger,
    UncertaintyRecord,
)
from tests import checks


def test_uncertainty_bounds_match_workbook_cells(tmp_path: Path) -> None:
    """A workbook hash cannot stand in for verifying the cited bound cells."""
    path = tmp_path / "source.xlsx"
    book = Workbook()
    sheet = book.active
    if sheet is None:
        raise AssertionError
    sheet["A1"], sheet["B1"], sheet["C1"] = 1, 2, 3
    book.save(path)
    book.close()
    digest = sha256(path.read_bytes()).hexdigest()
    source = SourceRecord(
        source_id="wb",
        sha256=digest,
        edition="v1",
        locator="WB01:A1:C1",
        limitations="synthetic",
    )
    parameter = Parameter(
        parameter_id="p",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256=digest,
        source_locator="WB01:B1",
        transformation="identity",
        uncertainty="synthetic",
        status="observed",
    )
    params = ParameterSet(
        version_id="v1",
        workbook_sha256=digest,
        parameters=(parameter,),
    )
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic",
        source=source,
    )
    record = UncertaintyRecord(
        measure_id="p",
        unit="h",
        source=source,
        lower=BoundValue(value=Decimal(1), locator="WB01:A1", absence_reason=None),
        midpoint=BoundValue(value=Decimal(2), locator="WB01:B1", absence_reason=None),
        upper=BoundValue(value=Decimal(3), locator="WB01:C1", absence_reason=None),
        interpretation="reported_range",
        interpretation_evidence=declared,
        distribution=declared,
        dependence=declared,
    )
    ledger = UncertaintyLedger(parameter_set=params, records=(record,))
    ledger.verify_required(("p",), {"wb": path})
    wrong = record.model_copy(
        update={"upper": record.upper.model_copy(update={"locator": "WB01:B1"})},
    )
    with pytest.raises(ValueError, match="bound source"):
        UncertaintyLedger(parameter_set=params, records=(wrong,)).verify_required(
            ("p",),
            {"wb": path},
        )


def test_uncertainty_ledger_binds_parameter_and_source_bytes(tmp_path: Path) -> None:
    """Coverage and exact source bytes are required before use of declarations."""
    snapshot = tmp_path / "source.txt"
    snapshot.write_text("1\n2\n3\n", encoding="utf-8")
    digest = sha256(snapshot.read_bytes()).hexdigest()
    source = SourceRecord(
        source_id="s",
        sha256=digest,
        edition="v1",
        locator="line 1",
        limitations="synthetic",
    )
    parameter = Parameter(
        parameter_id="p",
        raw_value="2",
        derived_value="2",
        unit="h",
        source_sha256=digest,
        source_locator="line 1",
        transformation="identity",
        uncertainty="synthetic",
        status="observed",
    )
    parameters = ParameterSet(
        version_id="v1",
        workbook_sha256="a" * 64,
        parameters=(parameter,),
    )
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic assertion",
        source=source,
    )
    record = UncertaintyRecord(
        measure_id="p",
        unit="h",
        source=source,
        lower=BoundValue(value=Decimal(1), locator="line 1", absence_reason=None),
        midpoint=BoundValue(value=Decimal(2), locator="line 2", absence_reason=None),
        upper=BoundValue(value=Decimal(3), locator="line 3", absence_reason=None),
        interpretation="reported_range",
        interpretation_evidence=declared,
        distribution=declared,
        dependence=declared,
    )
    ledger = UncertaintyLedger(parameter_set=parameters, records=(record,))
    ledger.verify_required(("p",), {"s": snapshot})
    forged_bound = record.model_copy(
        update={"lower": record.lower.model_copy(update={"value": Decimal(0)})},
    )
    with pytest.raises(ValueError, match="bound source"):
        UncertaintyLedger(
            parameter_set=parameters,
            records=(forged_bound,),
        ).verify_required(
            ("p",),
            {"s": snapshot},
        )
    with pytest.raises(ValueError, match="snapshot missing"):
        ledger.verify_required(("p",), {})
    with pytest.raises(ValueError, match="scope is empty or duplicated"):
        ledger.verify_required(("p", "p"), {"s": snapshot})
    conflicting = declared.model_copy(
        update={"source": source.model_copy(update={"edition": "other"})},
    )
    changed = record.model_copy(update={"dependence": conflicting})
    with pytest.raises(ValueError, match="Conflicting"):
        UncertaintyLedger(parameter_set=parameters, records=(changed,)).verify_required(
            ("p",),
            {"s": snapshot},
        )
    with pytest.raises(ValueError, match="coverage"):
        UncertaintyLedger(parameter_set=parameters, records=())
    with pytest.raises(ValueError, match="midpoint"):
        UncertaintyLedger(
            parameter_set=parameters,
            records=(
                record.model_copy(
                    update={
                        "midpoint": record.midpoint.model_copy(
                            update={"value": Decimal("2.5")},
                        ),
                    },
                ),
            ),
        )
    with pytest.raises(ValueError, match="unit"):
        UncertaintyLedger(
            parameter_set=parameters,
            records=(record.model_copy(update={"unit": "min"}),),
        )
    with pytest.raises(ValueError, match="coverage"):
        ledger.model_copy(update={"records": ()}).verify_required(
            ("p",),
            {"s": snapshot},
        )
    snapshot.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        ledger.verify_required(("p",), {"s": snapshot})


def test_bounds_and_unresolved_uncertainty_remain_explicit() -> None:
    """Source ranges do not imply a distribution or independent inputs."""
    source = SourceRecord(
        source_id="workbook",
        sha256="a" * 64,
        edition="v1",
        locator="WB17:M5:O5",
        limitations="synthetic",
    )
    absent = EvidenceDeclaration(state="unresolved", description=None, source=None)
    record = UncertaintyRecord(
        measure_id="resource-cost",
        unit="AUD/test",
        source=source,
        lower=BoundValue(value=Decimal(1), locator="WB17:M5", absence_reason=None),
        midpoint=BoundValue(value=Decimal(2), locator="WB17:N5", absence_reason=None),
        upper=BoundValue(value=Decimal(3), locator="WB17:O5", absence_reason=None),
        interpretation="unresolved",
        interpretation_evidence=absent,
        distribution=absent,
        dependence=absent,
    )
    with pytest.raises(ValueError, match="interpretation"):
        record.require_specified()
    with pytest.raises(ValidationError):
        record.unit = "other"
    with pytest.raises(ValueError, match="ordered"):
        UncertaintyRecord.model_validate(
            record.model_dump()
            | {"upper": {"value": "0", "locator": "WB17:O5", "absence_reason": None}},
        )
    with pytest.raises(ValueError, match="finite"):
        BoundValue(value=Decimal("NaN"), locator="WB17:M5", absence_reason=None)
    with pytest.raises(ValueError, match="absence"):
        BoundValue(value=None, locator="WB17:M5", absence_reason=None)
    missing = BoundValue(value=None, locator="WB17:M5", absence_reason="source blank")
    checks.require_equal(missing.value, None)
    with pytest.raises(ValueError, match="evidence"):
        EvidenceDeclaration(state="declared", description="independent", source=None)
    declared = EvidenceDeclaration(
        state="declared",
        description="synthetic assumption",
        source=source,
    )
    specified = UncertaintyRecord.model_validate(
        record.model_dump()
        | {
            "interpretation": "reported_range",
            "interpretation_evidence": declared.model_dump(),
            "distribution": declared.model_dump(),
            "dependence": declared.model_dump(),
        },
    )
    specified.require_specified()
    forged = specified.model_copy(update={"upper": missing})
    with pytest.raises(ValueError, match="bounds"):
        forged.require_specified()
