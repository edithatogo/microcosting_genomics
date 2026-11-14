# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check the resource-to-source comparison integration seam."""

from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from genomics_microcosting.provenance_ledger import (
    InputManifest,
    InputRequirement,
    Parameter,
    ParameterQualification,
    ParameterSet,
    SourceRecord,
)
from genomics_microcosting.resource_accounting import (
    BaselineDisposition,
    DraftParameterBindings,
    DraftResourceComparison,
    ResourceLine,
    ResourceParameterBinding,
)
from genomics_microcosting.resource_comparison import (
    ResourceComparisonRequest,
    compare_source_checked_resource_draft,
)
from tests import checks
lazy from genomics_microcosting.parameter_provenance import EvidenceComparison
lazy from genomics_microcosting.scenario_comparison import (
    ComparisonSources,
    QualificationContext,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_resource_bridge_checks_values_scope_and_observation_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stubbed source verifier tests only the arithmetic/qualification seam."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="1",
        locator="line 1",
        limitations="synthetic",
    )

    def param(name: str, value: str, unit: str) -> Parameter:
        return Parameter(
            parameter_id=name,
            raw_value=value,
            derived_value=value,
            unit=unit,
            source_sha256="a" * 64,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="observed",
        )

    params = tuple(
        param(*p)
        for p in (
            ("q", "2", "item/sample"),
            ("p", "3", "AUD/item"),
            ("a", "1", "fraction"),
            ("t", "6", "AUD/sample"),
        )
    )
    paramset = ParameterSet(
        version_id="v1",
        workbook_sha256="b" * 64,
        parameters=params,
    )
    qualifications = tuple(
        ParameterQualification(
            parameter=p,
            source=source,
            exact_support="synthetic",
            dimensional_basis="synthetic",
            applicability="synthetic",
            qualification="qualified",
            blockers=(),
        )
        for p in params
    )
    items = tuple(
        InputRequirement(
            input_id=p.parameter_id,
            resource_id="kit",
            role="synthetic",
            parameter=p,
            qualification=q,
            blockers=(),
        )
        for p, q in zip(params, qualifications, strict=True)
    )
    manifest = InputManifest(
        version_id="m1",
        candidate_id="C1",
        workbook_sha256="b" * 64,
        scope="synthetic",
        required_ids=tuple(p.parameter_id for p in params),
        inputs=items,
    )
    line = ResourceLine(
        resource_id="kit",
        quantity=Decimal(2),
        quantity_unit="item",
        unit_cost=Decimal(3),
        cost_denominator_unit="item",
        currency="AUD",
        allocation=Decimal(1),
    )
    disposition = BaselineDisposition(
        baseline_resource_id="kit",
        action="retained",
        candidate_resource_ids=("kit",),
        residual_treatment="none",
        stranded_resource_ids=(),
    )
    draft = DraftResourceComparison(
        baseline=(line,),
        candidate=(line,),
        dispositions=(disposition,),
        added_candidate_ids=(),
        baseline_total=Decimal(6),
        functional_unit="sample",
        currency="AUD",
    )
    bind = ResourceParameterBinding(
        arm="baseline",
        resource_id="kit",
        quantity_parameter_id="q",
        unit_cost_parameter_id="p",
        allocation_parameter_id="a",
    )
    bindings = DraftParameterBindings(
        parameter_version_id="v1",
        baseline_total_parameter_id="t",
        lines=(bind, bind.model_copy(update={"arm": "candidate"})),
    )
    observation = SimpleNamespace(
        amount=Decimal(6),
        currency="AUD",
        denominator="sample",
    )
    checked = SimpleNamespace(
        baseline=observation,
        candidate=observation,
        delta=Decimal(0),
        uncertainty_status="bounds_and_source_bytes_checked",
    )
    calls: list[tuple[object, ...]] = []

    def source_verifier(*args: object) -> object:
        calls.append(args)
        return checked

    monkeypatch.setattr(
        "genomics_microcosting.resource_comparison.compare_qualified_scenario",
        source_verifier,
    )
    qualification = SimpleNamespace(
        manifest=manifest,
        uncertainty=object(),
        ledger=SimpleNamespace(parameter_set=paramset),
    )
    request = ResourceComparisonRequest(
        catalogue_path=tmp_path / "catalogue",
        scenario_id="S1",
        comparison=cast("EvidenceComparison", object()),
        sources=cast("ComparisonSources", object()),
        qualification=cast("QualificationContext", qualification),
        draft=draft,
        bindings=bindings,
    )
    result = compare_source_checked_resource_draft(request)
    checks.require_equal(len(calls), 1)
    checks.require_equal(len(result.resource_model_sha256), len("a" * 64))
    checked.candidate = SimpleNamespace(
        amount=Decimal(5),
        currency="AUD",
        denominator="sample",
    )
    with pytest.raises(ValueError, match="Resource totals"):
        compare_source_checked_resource_draft(request)
    qualification.uncertainty = None
    with pytest.raises(ValueError, match="declared uncertainty"):
        compare_source_checked_resource_draft(request)
