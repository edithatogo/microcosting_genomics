# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Project declared stock flows against rerun modeled workflow issue events.

All stock/open-life/issue rules require external qualification. The ledger does
not change schedules, place orders, dispose stock or prove complete material
coverage. Valuation uses remaining physical units, not all pack purchases.
"""

import json
from dataclasses import dataclass, field
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self
lazy from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.compute_cost import (
    ComputeCostContext,
    verify_numeric_source_values,
)
from genomics_microcosting.parameter_provenance import (
    Digest,
    NonEmpty,
)
from genomics_microcosting.workflow_schedule import (
    ResourceSchedulePolicy,
    ReworkScenario,
    WorkflowScenario,
    WorkflowSchedule,
    schedule_workflow,
    schedule_workflow_rework,
)
from genomics_microcosting.workload_contract import Workload

MAX_NUMERIC_DIGITS = 128


def _number(value: Decimal) -> Fraction:
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_NUMERIC_DIGITS
        or len(parts.digits) > MAX_NUMERIC_DIGITS
    ):
        msg = "Inventory number exceeds finite profile bounds"
        raise ValueError(msg)
    return Fraction(value)


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class InventoryItem(_Model):
    """Fix a material's discrete unit, pack size and explicit sharing rule."""

    item_id: NonEmpty
    unit_label: NonEmpty
    pack_capacity: int = Field(strict=True, gt=0)
    sharing_policy: Literal["known_open_life", "discard_after_issue"]
    open_life_seconds: Decimal | None = Field(gt=0, allow_inf_nan=False)


class StockPack(_Model):
    """One declared physical pack, including known initial partial inventory."""

    pack_id: NonEmpty
    lot_id: NonEmpty
    item_id: NonEmpty
    arrived_seconds: Decimal = Field(allow_inf_nan=False)
    sealed_expiry_seconds: Decimal | None = Field(allow_inf_nan=False)
    opening_state: Literal["sealed", "opened", "unknown"]
    opened_seconds: Decimal | None = Field(le=0, allow_inf_nan=False)
    remaining_units: int = Field(strict=True, ge=0)


class StockSnapshot(_Model):
    """A source-hashed view retaining evidence and scope limits."""

    format_version: Literal["inventory-stock-json-v1"]
    source_id: NonEmpty
    exporter_version: NonEmpty
    evidence_state: Literal["assumed", "reported", "observed"]
    scope_limit: NonEmpty
    time_origin_id: NonEmpty
    baseline_sha256: Digest
    items: tuple[InventoryItem, ...] = Field(max_length=1024)
    packs: tuple[StockPack, ...] = Field(max_length=10000)

    @model_validator(mode="after")
    def source_consistency(self) -> Self:
        """Reject aliases and inconsistent pack/opening history."""
        items = {item.item_id: item for item in self.items}
        if len(items) != len(self.items) or len(
            {p.pack_id for p in self.packs},
        ) != len(self.packs):
            msg = "Duplicate inventory item or pack identity"
            raise ValueError(msg)
        for item in self.items:
            if item.open_life_seconds is not None:
                _number(item.open_life_seconds)
        for pack in self.packs:
            if pack.item_id not in items:
                msg = "Pack references an unknown item"
                raise ValueError(msg)
            capacity = items[pack.item_id].pack_capacity
            arrival = _number(pack.arrived_seconds)
            if pack.sealed_expiry_seconds is not None:
                _number(pack.sealed_expiry_seconds)
            if (
                pack.remaining_units > capacity
                or (
                    pack.opening_state == "sealed"
                    and (
                        pack.opened_seconds is not None
                        or pack.remaining_units != capacity
                    )
                )
                or (pack.opening_state == "unknown" and pack.opened_seconds is not None)
            ):
                msg = "Pack remaining units contradict sealed/opened capacity"
                raise ValueError(msg)
            if (
                pack.opened_seconds is not None
                and _number(pack.opened_seconds) < arrival
            ):
                msg = "Initial pack opening precedes its arrival"
                raise ValueError(msg)
        return self


class MaterialRule(_Model):
    """A discrete run/member/control issue driver."""

    rule_id: NonEmpty
    stage_id: NonEmpty
    item_id: NonEmpty
    unit_label: NonEmpty
    driver: Literal["per_run", "per_member", "per_control"]
    units_per_driver: int = Field(strict=True, gt=0)
    issue_offset_seconds: Decimal = Field(ge=0, allow_inf_nan=False)


class InventoryPlan(_Model):
    """Pin scope, time origin, source and material assumptions."""

    format_version: Literal["inventory-allocation-v1"]
    policy_id: NonEmpty
    parameter_version_id: NonEmpty
    baseline_sha256: Digest
    process_graph_sha256: Digest
    stock_source_sha256: Digest
    time_origin_id: NonEmpty
    scope: Literal["declared_materials_only"]
    assumption_basis: NonEmpty
    rules: tuple[MaterialRule, ...] = Field(max_length=128)


@dataclass(frozen=True)
class WorkflowInputs:
    """Retain workflow inputs for recomputation."""

    graph_payload: bytes
    workload: Workload
    policy: ResourceSchedulePolicy
    scenario: WorkflowScenario | ReworkScenario


@dataclass(frozen=True)
class InventoryInputs:
    """Retain source bytes and rules for recomputation."""

    workflow: WorkflowInputs
    stock_payload: bytes
    plan: InventoryPlan


@dataclass(frozen=True)
class StockFlowEvent:
    """Record modeled opening, issue, expiry or discard scope."""

    pack_id: str
    item_id: str
    kind: Literal["opened", "consumed", "expired", "discarded"]
    classified_at_seconds: Fraction
    trigger_seconds: Fraction | None
    units: int
    operation_id: str | None
    reason: str


@dataclass(frozen=True)
class MaterialIssue:
    """An aggregated stage/item issue preserving unfilled modeled demand."""

    operation_id: str
    stage_id: str
    item_id: str
    issue_seconds: Fraction
    rule_ids: tuple[str, ...]
    required_units: int
    supplied_units: int
    unfilled_units: int


@dataclass(frozen=True)
class PackBalance:
    """Conserve source remaining units; exclude prior depletion."""

    pack_id: str
    item_id: str
    lot_id: str
    source_units: int
    consumed_units: int
    expired_units: int
    discarded_units: int
    closing_usable_units: int
    closing_unqualified_units: int
    not_received_units: int


@dataclass(frozen=True)
class InventoryAssessment:
    """Keep material sufficiency separate from scripted workflow completion."""

    input_sha256: str
    schedule: WorkflowSchedule
    stock: StockSnapshot
    plan: InventoryPlan
    source_scope_limit: str
    cost_scope: Literal["declared_materials_only"]
    issues: tuple[MaterialIssue, ...]
    packs: tuple[PackBalance, ...]
    events: tuple[StockFlowEvent, ...]
    material_status: Literal["fulfilled", "unfilled"]


@dataclass
class _Pack:
    source: StockPack
    item: InventoryItem
    remaining: int
    opened: Fraction | None
    consumed: int = 0
    expired: int = 0
    discarded: int = 0
    events: list[StockFlowEvent] = field(default_factory=list)

    def deadline(self) -> Fraction | None:
        limits: list[Fraction] = []
        if self.source.sealed_expiry_seconds is not None:
            limits.append(_number(self.source.sealed_expiry_seconds))
        if self.opened is not None and self.item.open_life_seconds is not None:
            limits.append(self.opened + _number(self.item.open_life_seconds))
        return min(limits) if limits else None

    def advance(self, time: Fraction, horizon: Fraction) -> None:
        arrival = _number(self.source.arrived_seconds)
        if arrival >= horizon or arrival > time or self.remaining == 0:
            return
        deadline = self.deadline()
        if deadline is not None and deadline <= time:
            self.expired += self.remaining
            self.events.append(
                StockFlowEvent(
                    self.source.pack_id,
                    self.item.item_id,
                    "expired",
                    time,
                    deadline,
                    self.remaining,
                    None,
                    "known_expiry_bound",
                ),
            )
            self.remaining = 0
        elif (
            self.opened is not None or self.source.opening_state == "opened"
        ) and self.item.sharing_policy == "discard_after_issue":
            self.discard(time, None, "preopened_single_issue_remainder")

    def usable(self, time: Fraction, horizon: Fraction) -> bool:
        if (
            self.remaining == 0
            or self.source.opening_state == "unknown"
            or (self.source.opening_state == "opened" and self.opened is None)
            or _number(self.source.arrived_seconds) > time
            or _number(self.source.arrived_seconds) >= horizon
            or self.source.sealed_expiry_seconds is None
        ):
            return False
        if (
            self.item.sharing_policy == "known_open_life"
            and self.item.open_life_seconds is None
        ):
            return False
        deadline = self.deadline()
        return deadline is not None and deadline > time

    def discard(
        self,
        time: Fraction,
        operation: str | None,
        reason: str,
    ) -> None:
        if self.remaining:
            self.discarded += self.remaining
            self.events.append(
                StockFlowEvent(
                    self.source.pack_id,
                    self.item.item_id,
                    "discarded",
                    time,
                    None,
                    self.remaining,
                    operation,
                    reason,
                ),
            )
            self.remaining = 0

    def issue(self, wanted: int, time: Fraction, operation: str) -> int:
        if self.opened is None:
            self.opened = time
            self.events.append(
                StockFlowEvent(
                    self.source.pack_id,
                    self.item.item_id,
                    "opened",
                    time,
                    time,
                    0,
                    operation,
                    "modeled_first_issue",
                ),
            )
        units = min(wanted, self.remaining)
        self.consumed += units
        self.remaining -= units
        self.events.append(
            StockFlowEvent(
                self.source.pack_id,
                self.item.item_id,
                "consumed",
                time,
                time,
                units,
                operation,
                "declared_stage_demand",
            ),
        )
        if self.item.sharing_policy == "discard_after_issue":
            self.discard(time, operation, "single_issue_remainder")
        return units

    def close(self, horizon: Fraction) -> PackBalance:
        self.advance(horizon, horizon)
        future = (
            self.remaining if _number(self.source.arrived_seconds) >= horizon else 0
        )
        usable = self.remaining if not future and self.usable(horizon, horizon) else 0
        unqualified = self.remaining - future - usable
        balance = PackBalance(
            self.source.pack_id,
            self.item.item_id,
            self.source.lot_id,
            self.source.remaining_units,
            self.consumed,
            self.expired,
            self.discarded,
            usable,
            unqualified,
            future,
        )
        if balance.source_units != sum(
            (
                self.consumed,
                self.expired,
                self.discarded,
                usable,
                unqualified,
                future,
            ),
        ):
            msg = "Inventory unit conservation failed"
            raise ArithmeticError(msg)
        return balance


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate inventory JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def _validate_rules(
    plan: InventoryPlan,
    stock: StockSnapshot,
    workflow: WorkflowInputs,
) -> None:
    items = {i.item_id: i for i in stock.items}
    timings = {
        t.stage_id: t
        for t in ResourceSchedulePolicy.model_validate(workflow.policy).timings
    }
    keys = {
        (r.stage_id, r.item_id, r.driver, _number(r.issue_offset_seconds))
        for r in plan.rules
    }
    if len({r.rule_id for r in plan.rules}) != len(plan.rules) or len(
        keys,
    ) != len(plan.rules):
        msg = "Duplicate material rule identity or aliased driver"
        raise ValueError(msg)
    for rule in plan.rules:
        if (
            rule.item_id not in items
            or rule.stage_id not in timings
            or rule.unit_label != items[rule.item_id].unit_label
            or _number(rule.issue_offset_seconds)
            >= _number(timings[rule.stage_id].duration_seconds)
        ):
            msg = "Material rule stage, unit or issue interval is invalid"
            raise ValueError(msg)


def _requirements(
    schedule: WorkflowSchedule,
    plan: InventoryPlan,
) -> list[tuple[Fraction, str, str, str, tuple[str, ...], int]]:
    combined: dict[tuple[Fraction, str, str, str], tuple[list[str], int]] = {}
    for run in schedule.runs:
        for rule in plan.rules:
            if rule.stage_id != run.stage_id:
                continue
            driver = {
                "per_run": 1,
                "per_member": len(run.members),
                "per_control": run.control_slots,
            }[rule.driver]
            count = driver * rule.units_per_driver
            if not count:
                continue
            key = (
                run.start_seconds + _number(rule.issue_offset_seconds),
                run.operation_id,
                run.stage_id,
                rule.item_id,
            )
            ids, previous = combined.get(key, ([], 0))
            combined[key] = ([*ids, rule.rule_id], previous + count)
    return [(*key, tuple(ids), count) for key, (ids, count) in sorted(combined.items())]


def _assess(
    inputs: InventoryInputs,
) -> tuple[InventoryAssessment, StockSnapshot]:
    plan = InventoryPlan.model_validate(inputs.plan)
    workflow = inputs.workflow
    if sha256(inputs.stock_payload).hexdigest() != plan.stock_source_sha256:
        msg = "Inventory source hash mismatch"
        raise ValueError(msg)
    stock = StockSnapshot.model_validate(
        json.loads(
            inputs.stock_payload,
            parse_float=Decimal,
            object_pairs_hook=_unique_fields,
        ),
    )
    if isinstance(workflow.scenario, ReworkScenario):
        schedule = schedule_workflow_rework(
            workflow.graph_payload,
            workflow.workload,
            workflow.policy,
            workflow.scenario,
        )
    else:
        schedule = schedule_workflow(
            workflow.graph_payload,
            workflow.workload,
            workflow.policy,
            workflow.scenario,
        )
    if (
        plan.baseline_sha256 != stock.baseline_sha256
        or plan.time_origin_id != stock.time_origin_id
        or plan.process_graph_sha256 != schedule.process_graph_sha256
        or plan.parameter_version_id != schedule.parameter_version_id
    ):
        msg = "Inventory baseline, time or workflow identity mismatch"
        raise ValueError(msg)
    _validate_rules(plan, stock, workflow)
    horizon = _number(
        Workload.model_validate(workflow.workload).horizon_seconds,
    )
    items = {i.item_id: i for i in stock.items}
    events: list[StockFlowEvent] = []
    states = [
        _Pack(
            p,
            items[p.item_id],
            p.remaining_units,
            None if p.opened_seconds is None else _number(p.opened_seconds),
            events=events,
        )
        for p in stock.packs
    ]
    issues: list[MaterialIssue] = []
    for time, operation, stage, item, rules, required in _requirements(
        schedule,
        plan,
    ):
        candidates = [p for p in states if p.item.item_id == item]
        for pack in candidates:
            pack.advance(time, horizon)
        eligible = [p for p in candidates if p.usable(time, horizon)]
        eligible.sort(
            key=lambda p: (
                p.deadline(),
                _number(p.source.arrived_seconds),
                p.source.pack_id,
            ),
        )
        supplied = 0
        for pack in eligible:
            supplied += pack.issue(required - supplied, time, operation)
            if supplied == required:
                break
        issues.append(
            MaterialIssue(
                operation,
                stage,
                item,
                time,
                rules,
                required,
                supplied,
                required - supplied,
            ),
        )
    balances = tuple(p.close(horizon) for p in states)
    identity = {
        "schedule": schedule.input_sha256,
        "plan": plan.model_dump(mode="json"),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    result = InventoryAssessment(
        digest,
        schedule,
        stock,
        plan,
        stock.scope_limit,
        "declared_materials_only",
        tuple(issues),
        balances,
        tuple(events),
        "unfilled" if any(i.unfilled_units for i in issues) else "fulfilled",
    )
    return result, stock


def assess_inventory(inputs: InventoryInputs) -> InventoryAssessment:
    """Rerun the workflow and conserve source stock under declared issue rules.

    No shortage turns a scripted outcome into verified completion.
    Retain material status and resource/workflow feasibility separately.

    Args:
        inputs: Exact source bytes, declared rules and original workflow inputs.

    Returns:
        Projected issues, source/rules and conserved stock flows.

    Raises:
        ValueError: Source, identity, units, rules or workflow validation fails.
        ArithmeticError: Internal projected unit conservation fails.

    """
    return _assess(inputs)[0]


class LotPriceBinding(_Model):
    """Select one retained pack-price parameter for an exact item/lot pair."""

    item_id: NonEmpty
    lot_id: NonEmpty
    parameter_id: NonEmpty


class InventoryPricing(_Model):
    """Declare one currency/year/tax basis without inferring normalization."""

    format_version: Literal["inventory-value-v1"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive"]
    bindings: tuple[LotPriceBinding, ...]


@dataclass(frozen=True)
class InventoryValue:
    """Value all remaining-stock flows without expensing unconsumed packs."""

    input_sha256: str
    inventory: InventoryAssessment
    currency: str
    price_year: int
    tax_basis: Literal["inclusive", "exclusive"]
    cost_scope: Literal["declared_materials_only"]
    consumed_stock_value: Fraction
    expired_stock_value: Fraction
    discarded_stock_value: Fraction
    closing_usable_value: Fraction
    closing_unqualified_value: Fraction
    not_received_value: Fraction
    declared_remaining_value: Fraction


def value_inventory(
    inputs: InventoryInputs,
    pricing: InventoryPricing,
    context: ComputeCostContext,
) -> InventoryValue:
    """Value recomputed lot flows from dated numeric sources.

    These are stock-flow values, not procurement cash or all-workload costs.
    No period expense, fair value or per-test unit cost is inferred.

    Args:
        inputs: Original workflow, stock bytes and proposed issue rules.
        pricing: Exact lot bindings and declared currency/year/tax basis.
        context: Selected numeric rate sources, qualification and valid dates.

    Returns:
        Exact values for consumed, expired, discarded and retained stock units.

    Raises:
        ValueError: Quantity/source/basis, rate, identity or validity fails.
        ArithmeticError: Internal projected value conservation fails.
        OSError: An explicitly selected numeric rate source cannot be read.

    """
    pricing = InventoryPricing.model_validate(pricing)
    result, stock = _assess(inputs)
    if (
        context.ledger.parameter_set.workbook_sha256 != stock.baseline_sha256
        or context.ledger.parameter_set.version_id
        != result.schedule.parameter_version_id
    ):
        msg = "Inventory price baseline/parameter version mismatch"
        raise ValueError(msg)
    values = verify_numeric_source_values(context)
    bindings = {(b.item_id, b.lot_id): b.parameter_id for b in pricing.bindings}
    keys = {(p.item_id, p.lot_id) for p in stock.packs}
    if (
        bindings.keys() != keys
        or len(bindings) != len(pricing.bindings)
        or set(bindings.values()) != values.keys()
    ):
        msg = "Inventory lot/parameter pricing coverage differs"
        raise ValueError(msg)
    capacities = {i.item_id: i.pack_capacity for i in stock.items}
    totals = [Fraction(0) for _ in range(7)]
    for pack in result.packs:
        rate, unit = values[bindings[(pack.item_id, pack.lot_id)]]
        if rate < 0 or unit != f"{pricing.currency}/pack:{pack.item_id}":
            msg = "Inventory pack rate is negative or has incompatible units"
            raise ValueError(msg)
        unit_value = _number(rate) / capacities[pack.item_id]
        quantities = (
            pack.consumed_units,
            pack.expired_units,
            pack.discarded_units,
            pack.closing_usable_units,
            pack.closing_unqualified_units,
            pack.not_received_units,
            pack.source_units,
        )
        totals = [
            total + quantity * unit_value
            for total, quantity in zip(totals, quantities, strict=True)
        ]
    if sum(totals[:-1]) != totals[-1]:
        msg = "Inventory stock value conservation failed"
        raise ArithmeticError(msg)
    identity = {
        "inventory": result.input_sha256,
        "pricing": pricing.model_dump(mode="json"),
        "ledger": context.ledger.model_dump(mode="json"),
        "validity": [v.model_dump(mode="json") for v in context.validity],
        "costing_date": context.costing_date.isoformat(),
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return InventoryValue(
        digest,
        result,
        pricing.currency,
        pricing.price_year,
        pricing.tax_basis,
        "declared_materials_only",
        *totals,
    )
