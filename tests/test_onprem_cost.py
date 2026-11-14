# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check annual platform costs and capacity allocation against exact oracles."""

from datetime import date
from fractions import Fraction
from hashlib import sha256
lazy from pathlib import Path

import pytest

from genomics_microcosting.compute_cost import ComputeCostContext
from genomics_microcosting.onprem_cost import (
    OnPremBinding,
    OnPremPricing,
    calculate_onprem_cost,
)
from genomics_microcosting.provenance_ledger import (
    Parameter,
    ParameterQualification,
    ParameterSet,
    QualificationLedger,
    SourceRecord,
    SourceValidity,
)
from tests import checks
lazy from genomics_microcosting.onprem_cost import Role


def platform_inputs(
    tmp_path: Path,
    **overrides: str,
) -> tuple[OnPremPricing, ComputeCostContext]:
    """Provide explicit synthetic annual costs and capacities, not observed prices."""
    data: dict[Role, tuple[str, str]] = {
        "acquisition": ("1000", "AUD"),
        "residual": ("0", "AUD"),
        "life": ("5", "year"),
        "interest": ("0", "fraction"),
        "support": ("100", "AUD/year"),
        "licensing": ("50", "AUD/year"),
        "power": ("100", "kWh/year"),
        "cooling": ("50", "kWh/year"),
        "energy_rate": ("2", "AUD/kWh"),
        "facilities": ("50", "AUD/year"),
        "available": ("100", "core_s/year"),
        "used": ("60", "core_s/year"),
        "workload": ("20", "core_s/year"),
    }
    params: list[Parameter] = []
    quals: list[ParameterQualification] = []
    validity: list[SourceValidity] = []
    paths: dict[str, Path] = {}
    bindings: list[OnPremBinding] = []
    for role, (default, unit) in data.items():
        value = overrides.get(role, default)
        path = tmp_path / f"{role}.txt"
        path.write_text(value + "\n", encoding="utf-8")
        digest = sha256(path.read_bytes()).hexdigest()
        source = SourceRecord(
            source_id=role,
            sha256=digest,
            edition="synthetic",
            locator="line 1",
            limitations="synthetic",
        )
        p = Parameter(
            parameter_id=role,
            raw_value=value,
            derived_value=value,
            unit=unit,
            source_sha256=digest,
            source_locator="line 1",
            transformation="identity",
            uncertainty="synthetic",
            status="reported",
        )
        params.append(p)
        quals.append(
            ParameterQualification(
                parameter=p,
                source=source,
                exact_support=value,
                dimensional_basis=unit,
                applicability="synthetic",
                qualification="qualified",
                blockers=(),
            ),
        )
        validity.append(
            SourceValidity(
                source=source,
                retrieved=date(2026, 11, 6),
                effective_from=date(2026, 1, 1),
                effective_until=date(2026, 12, 31),
                date_basis="synthetic",
            ),
        )
        paths[role] = path
        bindings.append(OnPremBinding(role=role, parameter_id=role))
    context = ComputeCostContext(
        QualificationLedger(
            parameter_set=ParameterSet(
                version_id="v1",
                workbook_sha256="f" * 64,
                parameters=tuple(params),
            ),
            qualifications=tuple(quals),
        ),
        paths,
        tuple(validity),
        date(2026, 6, 1),
    )
    pricing = OnPremPricing(
        platform_id="synthetic-host",
        workload_id="w1",
        currency="AUD",
        price_year=2026,
        tax_basis="inclusive",
        capacity_unit="core_s",
        annualization="straight_line",
        allocation_basis="available_capacity",
        bindings=tuple(bindings),
        assumption_basis="synthetic annual platform scope; no empirical claim",
    )
    return pricing, context


def test_annual_capacity_and_usage_allocation_conserve_cost(tmp_path: Path) -> None:
    """Reconcile 700 annual cost across explicitly supplied cost components."""
    pricing, context = platform_inputs(tmp_path)
    result = calculate_onprem_cost(pricing, context)
    checks.require_equal(result.total_annual_cost, Fraction(700))
    checks.require_equal(result.workload_cost, Fraction(140))
    checks.require_equal(result.other_used_cost, Fraction(280))
    checks.require_equal(result.unallocated_cost, Fraction(280))
    checks.require_equal(result.idle_capacity_cost, Fraction(280))
    usage = calculate_onprem_cost(
        pricing.model_copy(update={"allocation_basis": "used_capacity"}),
        context,
    )
    checks.require_equal(usage.workload_cost, Fraction(700, 3))
    checks.require_equal(usage.other_used_cost, Fraction(1400, 3))
    checks.require_equal(usage.unallocated_cost, Fraction(0))
    checks.require_equal(usage.idle_capacity_cost, Fraction(280))
    for outcome in (result, usage):
        checks.require_equal(
            outcome.workload_cost + outcome.other_used_cost + outcome.unallocated_cost,
            outcome.total_annual_cost,
        )


def test_annuity_and_idle_platform_cases_are_explicit(tmp_path: Path) -> None:
    """Capital recovery and empty use retain exact costs without zero unit rates."""
    pricing, context = platform_inputs(tmp_path, interest="0.1")
    with pytest.raises(ValueError, match="interest"):
        calculate_onprem_cost(pricing, context)
    result = calculate_onprem_cost(
        pricing.model_copy(update={"annualization": "annuity"}),
        context,
    )
    checks.require_equal(
        dict(result.annual_components)["capital"],
        Fraction(16105100, 61051),
    )
    pricing, context = platform_inputs(tmp_path, used="0", workload="0")
    idle = calculate_onprem_cost(
        pricing.model_copy(update={"allocation_basis": "used_capacity"}),
        context,
    )
    checks.require_equal(idle.unit_rate, None)
    checks.require_equal(idle.unallocated_cost, Fraction(700))
    pricing, context = platform_inputs(tmp_path, available="0", used="0", workload="0")
    empty = calculate_onprem_cost(pricing, context)
    checks.require_equal(empty.unit_rate, None)
    checks.require_equal(empty.idle_capacity_cost, None)
    checks.require_equal(empty.unallocated_cost, Fraction(700))


def test_capacity_scope_and_sources_cannot_be_invented(tmp_path: Path) -> None:
    """Invalid capacity chains, duplicate roles and changed source bytes fail."""
    for values in ({"used": "101"}, {"workload": "61"}, {"life": "0"}):
        pricing, context = platform_inputs(tmp_path, **values)
        with pytest.raises(ValueError, match=r"capacity|life"):
            calculate_onprem_cost(pricing, context)
    pricing, context = platform_inputs(tmp_path)
    with pytest.raises(ValueError, match="units"):
        calculate_onprem_cost(pricing.model_copy(update={"currency": "USD"}), context)
    duplicate = pricing.model_copy(update={"bindings": (pricing.bindings[0],) * 12})
    with pytest.raises(ValueError, match="coverage"):
        calculate_onprem_cost(duplicate, context)
    context.snapshots["power"].write_text("101\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        calculate_onprem_cost(pricing, context)


def test_residual_value_is_an_explicit_capital_input(tmp_path: Path) -> None:
    """Do not assume zero end-of-life value when annualizing acquisition."""
    pricing, context = platform_inputs(tmp_path, residual="100")
    result = calculate_onprem_cost(pricing, context)
    checks.require_equal(result.total_annual_cost, Fraction(680))
    pricing, context = platform_inputs(tmp_path, residual="100", interest="0.1")
    annuity = calculate_onprem_cost(
        pricing.model_copy(update={"annualization": "annuity"}),
        context,
    )
    checks.require_equal(
        dict(annuity.annual_components)["capital"],
        Fraction(15105100, 61051),
    )
