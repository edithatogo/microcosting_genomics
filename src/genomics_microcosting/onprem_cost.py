# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Source-checked annual platform costs with explicit idle-capacity allocation."""

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
lazy from genomics_microcosting.parameter_provenance import NonEmpty

Role = Literal[
    "acquisition",
    "residual",
    "life",
    "interest",
    "support",
    "licensing",
    "power",
    "cooling",
    "energy_rate",
    "facilities",
    "available",
    "used",
    "workload",
]
ROLE_UNITS: tuple[tuple[Role, str], ...] = (
    ("acquisition", "currency"),
    ("residual", "currency"),
    ("life", "year"),
    ("interest", "fraction"),
    ("support", "currency/year"),
    ("licensing", "currency/year"),
    ("power", "kWh/year"),
    ("cooling", "kWh/year"),
    ("energy_rate", "currency/kWh"),
    ("facilities", "currency/year"),
    ("available", "capacity/year"),
    ("used", "capacity/year"),
    ("workload", "capacity/year"),
)
MAX_ANNUITY_YEARS = 1000


class OnPremBinding(BaseModel):
    """Bind one declared annual cost/capacity role to a numeric source parameter."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    role: Role
    parameter_id: NonEmpty


class OnPremPricing(BaseModel):
    """Declare annual economics and allocation rather than infer local practice."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    format_version: Literal["on-prem-cost-v1"] = "on-prem-cost-v1"
    platform_id: NonEmpty
    workload_id: NonEmpty
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    capacity_unit: Literal["core_s", "device_s", "byte_s"]
    annualization: Literal["straight_line", "annuity"]
    allocation_basis: Literal["available_capacity", "used_capacity"]
    bindings: tuple[OnPremBinding, ...]
    assumption_basis: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"

    @model_validator(mode="after")
    def complete_roles(self) -> Self:
        """Require each cost/capacity role once and prohibit parameter reuse."""
        if (
            {b.role for b in self.bindings} != {r for r, _ in ROLE_UNITS}
            or len(self.bindings) != len(ROLE_UNITS)
            or len({b.parameter_id for b in self.bindings}) != len(self.bindings)
        ):
            msg = "On-prem role/input coverage is incomplete or duplicated"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class OnPremCost:
    """Conserve annual costs while exposing idle capacity and undefined rates."""

    input_sha256: str
    annual_components: tuple[tuple[str, Fraction], ...]
    total_annual_cost: Fraction
    unit_rate: Fraction | None
    workload_cost: Fraction
    other_used_cost: Fraction
    unallocated_cost: Fraction
    idle_capacity_cost: Fraction | None
    unused_capacity: Fraction


def _annual_capital(
    acquisition: Fraction,
    residual: Fraction,
    life: Fraction,
    interest: Fraction,
    method: str,
) -> Fraction:
    if life <= 0:
        msg = "On-prem useful life must be positive"
        raise ValueError(msg)
    if residual > acquisition:
        msg = "On-prem residual value exceeds acquisition value"
        raise ValueError(msg)
    if method == "straight_line":
        if interest != 0:
            msg = "Straight-line annualization cannot silently ignore interest"
            raise ValueError(msg)
        return (acquisition - residual) / life
    if interest == 0:
        return (acquisition - residual) / life
    if life.denominator != 1 or life > MAX_ANNUITY_YEARS:
        msg = "Positive-interest annuity life requires bounded whole years"
        raise ValueError(msg)
    factor = (1 + interest) ** life.numerator
    return interest * (acquisition * factor - residual) / (factor - 1)


def calculate_onprem_cost(
    pricing: OnPremPricing,
    context: ComputeCostContext,
) -> OnPremCost:
    """Price a declared annual platform scope without rounding rational rates."""
    pricing = OnPremPricing.model_validate(pricing.model_dump())
    raw = verify_numeric_source_values(context)
    identifiers = {b.role: b.parameter_id for b in pricing.bindings}
    if set(identifiers.values()) != raw.keys():
        msg = "On-prem source input coverage differs from selected ledger"
        raise ValueError(msg)
    values: dict[Role, Fraction] = {}
    for role, unit in ROLE_UNITS:
        value, actual_unit = raw[identifiers[role]]
        expected_unit = unit.replace("currency", pricing.currency).replace(
            "capacity",
            pricing.capacity_unit,
        )
        if value < 0 or actual_unit != expected_unit:
            msg = "On-prem input is negative or has incompatible units"
            raise ValueError(msg)
        values[role] = Fraction(value)
    capital = _annual_capital(
        values["acquisition"],
        values["residual"],
        values["life"],
        values["interest"],
        pricing.annualization,
    )
    available, used, workload = values["available"], values["used"], values["workload"]
    if not workload <= used <= available:
        msg = "On-prem capacity must satisfy workload <= used <= available"
        raise ValueError(msg)
    components = (
        ("capital", capital),
        ("support", values["support"]),
        ("licensing", values["licensing"]),
        ("power", values["power"] * values["energy_rate"]),
        ("cooling", values["cooling"] * values["energy_rate"]),
        ("facilities", values["facilities"]),
    )
    total = sum((cost for _, cost in components), Fraction())
    denominator = (
        available if pricing.allocation_basis == "available_capacity" else used
    )
    rate = None if denominator == 0 else total / denominator
    allocated = Fraction() if rate is None else rate * workload
    other = Fraction() if rate is None else rate * (used - workload)
    unallocated = total - allocated - other
    idle = None if available == 0 else total * (available - used) / available
    identity = {
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return OnPremCost(
        digest,
        components,
        total,
        rate,
        allocated,
        other,
        unallocated,
        idle,
        available - used,
    )
