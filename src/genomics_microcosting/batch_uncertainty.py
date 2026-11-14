# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Seeded sampling of explicitly assumed joint batch realizations."""

import json
import sys
from bisect import bisect_right
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from fractions import Fraction
from hashlib import sha256
from itertools import accumulate
from typing import Literal, Self, TypedDict, Unpack
lazy from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.dynamic_batch import AvailabilityWindow, DynamicBatchPolicy
from genomics_microcosting.static_batch_cost import (
    BatchPricing,
    DynamicBatchCost,
    calculate_dynamic_batch_cost,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.compute_cost import ComputeCostContext
lazy from genomics_microcosting.parameter_provenance import NonEmpty

MAX_DRAWS = 10000
MAX_SEED = 2**64 - 1
MAX_RESOURCE_DIGITS = 128
RESOURCE_SUMMARY_VERSION = "batch-resource-summary-v1"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key in joint scenario recipe"
            raise ValueError(msg)
        result[key] = value
    return result


class CaseArrival(BaseModel):
    """Declare a realized arrival for one existing case."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    case_id: NonEmpty
    seconds: Decimal = Field(ge=0, allow_inf_nan=False)


class JointBatchState(BaseModel):
    """Keep arrival, duration and availability assumptions together as one state."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    scenario_id: NonEmpty
    weight: int = Field(strict=True, gt=0, le=2**31 - 1)
    arrivals: tuple[CaseArrival, ...]
    run_duration_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    windows: tuple[AvailabilityWindow, ...]


class JointBatchEnsemble(BaseModel):
    """Define a finite assumed distribution without interpreting measured ranges."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    format_version: Literal["joint-batch-ensemble-v1"]
    assumption_basis: NonEmpty
    evidence_state: Literal["assumed"]
    states: tuple[JointBatchState, ...] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def unique_states(self) -> Self:
        """Reject ambiguous scenario identities and repeated case arrivals."""
        if len({s.scenario_id for s in self.states}) != len(self.states) or any(
            len({a.case_id for a in s.arrivals}) != len(s.arrivals) for s in self.states
        ):
            msg = "Duplicate joint state or case arrival"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class BatchResourceUse:
    """Describe finite-horizon machine occupancy and separate queue/slot use."""

    available_seconds: Fraction
    busy_seconds: Fraction
    idle_seconds: Fraction
    resource_utilization: Fraction | None
    payload_slot_fill: Fraction | None
    occupied_slot_fill: Fraction | None
    served_queue_waits: tuple[tuple[str, Fraction], ...]


@dataclass(frozen=True)
class BatchStateOutcome:
    """Retain complete state accounting and individual served-case turnaround."""

    scenario_id: str
    weight: int
    result: DynamicBatchCost
    turnarounds: tuple[tuple[str, Decimal], ...]
    resource_use: BatchResourceUse | None = None


@dataclass(frozen=True)
class BatchUncertaintyResult:
    """Separate exact assumed-distribution summaries from sampled state indices."""

    input_sha256: str
    recipe_sha256: str
    seed: int
    runtime: str
    outcomes: tuple[BatchStateOutcome, ...]
    draw_indices: tuple[int, ...]
    feasible_probability: Fraction
    mean_complete_service_cost: Fraction | None
    resource_summary_version: str | None = None
    mean_resource_utilization: Fraction | None = None
    pooled_resource_utilization: Fraction | None = None
    mean_complete_service_queue_wait_seconds: Fraction | None = None


def _time_fraction(value: Decimal) -> Fraction:
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_RESOURCE_DIGITS
        or len(parts.digits) > MAX_RESOURCE_DIGITS
    ):
        msg = "Joint-state resource time exceeds finite profile bounds"
        raise ValueError(msg)
    return Fraction(value)


def _resource_use(
    result: DynamicBatchCost,
    arrivals: dict[str, Decimal],
    policy: DynamicBatchPolicy,
) -> BatchResourceUse:
    available = sum(
        (
            _time_fraction(w.end_seconds) - _time_fraction(w.start_seconds)
            for w in policy.windows
        ),
        Fraction(),
    )
    runs = result.schedule.runs
    busy = sum(
        (
            _time_fraction(r.complete_seconds) - _time_fraction(r.start_seconds)
            for r in runs
        ),
        Fraction(),
    )
    payload = sum(len(r.case_ids) for r in runs)
    occupied = payload + sum(r.control_slots for r in runs)
    payload_slots = len(runs) * policy.batch.payload_limit
    physical_slots = len(runs) * policy.batch.capacity
    waits = tuple(
        (case_id, _time_fraction(run.start_seconds) - _time_fraction(arrivals[case_id]))
        for run in runs
        for case_id in run.case_ids
    )
    if (
        not 0 <= busy <= available
        or payload > payload_slots
        or occupied > physical_slots
        or any(wait < 0 for _, wait in waits)
    ):
        msg = "Joint-state resource accounting is inconsistent with its schedule"
        raise ValueError(msg)
    return BatchResourceUse(
        available,
        busy,
        available - busy,
        busy / available if available else None,
        Fraction(payload, payload_slots) if payload_slots else None,
        Fraction(occupied, physical_slots) if physical_slots else None,
        waits,
    )


def _resource_summaries(
    outcomes: tuple[BatchStateOutcome, ...],
    total_weight: int,
    cases: int,
) -> tuple[Fraction | None, Fraction | None, Fraction | None]:
    weighted: list[tuple[int, BatchResourceUse]] = []
    for outcome in outcomes:
        if outcome.resource_use is None:
            msg = "Joint-state resource summary is missing"
            raise ValueError(msg)
        weighted.append((outcome.weight, outcome.resource_use))
    mean = (
        sum(
            (
                w * u.resource_utilization
                for w, u in weighted
                if u.resource_utilization is not None
            ),
            Fraction(),
        )
        / total_weight
        if all(u.resource_utilization is not None for _, u in weighted)
        else None
    )
    available = sum((w * u.available_seconds for w, u in weighted), Fraction())
    busy = sum((w * u.busy_seconds for w, u in weighted), Fraction())
    pooled = busy / available if available else None
    mean_wait = (
        sum(
            (
                w * sum((wait for _, wait in u.served_queue_waits), Fraction())
                for w, u in weighted
            ),
            Fraction(),
        )
        / (total_weight * cases)
        if cases and all(o.result.cost_state == "complete_workload" for o in outcomes)
        else None
    )
    return mean, pooled, mean_wait


def _evaluate_state(
    state: JointBatchState,
    workload: Workload,
    policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
) -> BatchStateOutcome:
    arrivals = {a.case_id: a.seconds for a in state.arrivals}
    if arrivals.keys() != {c.case_id for c in workload.cases}:
        msg = "Joint scenario case coverage differs from the fixed workload"
        raise ValueError(msg)
    realized = workload.model_copy(
        update={
            "cases": tuple(
                c.model_copy(update={"arrival_seconds": arrivals[c.case_id]})
                for c in workload.cases
            ),
        },
    )
    selected = policy.model_copy(
        update={
            "run_duration_seconds": state.run_duration_seconds,
            "windows": state.windows,
        },
    )
    result = calculate_dynamic_batch_cost(realized, selected, pricing, context)
    with localcontext() as arithmetic:
        arithmetic.prec = 50
        arithmetic.traps[Inexact] = True
        turnarounds = tuple(
            (case_id, run.complete_seconds - arrivals[case_id])
            for run in result.schedule.runs
            for case_id in run.case_ids
        )
    return BatchStateOutcome(
        state.scenario_id,
        state.weight,
        result,
        turnarounds,
        _resource_use(result, arrivals, selected),
    )


class SamplingOptions(TypedDict):
    """Seed and draw count for reproducible finite-state sampling."""

    seed: int
    draws: int


def simulate_batch_uncertainty(
    recipe_path: Path,
    workload: Workload,
    policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
    **sampling: Unpack[SamplingOptions],
) -> BatchUncertaintyResult:
    """Evaluate every declared joint state then sample integer-weighted states.

    This is a proposed finite distribution, not an inference from bounds, an
    empirical probability estimate or a claim of stochastic convergence.
    """
    seed, draws = sampling["seed"], sampling["draws"]
    if (
        type(seed) is not int
        or not 0 <= seed <= MAX_SEED
        or type(draws) is not int
        or not 1 <= draws <= MAX_DRAWS
    ):
        msg = "Invalid sampling seed or draw bound"
        raise ValueError(msg)
    workload = Workload.model_validate(workload.model_dump())
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    payload = recipe_path.read_bytes()
    recipe_digest = sha256(payload).hexdigest()
    ensemble = JointBatchEnsemble.model_validate(
        json.loads(payload, parse_float=Decimal, object_pairs_hook=_unique_object),
    )
    outcomes = tuple(
        _evaluate_state(state, workload, policy, pricing, context)
        for state in ensemble.states
    )
    cumulative = tuple(accumulate(s.weight for s in ensemble.states))
    total = cumulative[-1]
    rng = np.random.Generator(np.random.PCG64(seed))
    indices = tuple(
        bisect_right(cumulative, int(value))
        for value in rng.integers(0, total, size=draws)
    )
    feasible = sum(
        o.weight for o in outcomes if o.result.schedule.feasibility == "feasible"
    )
    mean_cost = (
        sum(
            (Fraction(o.result.cost.total_cost) * o.weight for o in outcomes),
            Fraction(),
        )
        / total
        if all(o.result.cost_state == "complete_workload" for o in outcomes)
        else None
    )
    if sha256(recipe_path.read_bytes()).hexdigest() != recipe_digest:
        msg = "Joint scenario recipe changed during execution"
        raise ValueError(msg)
    identity = {
        "recipe_sha256": recipe_digest,
        "seed": seed,
        "draws": draws,
        "rng": "numpy.Generator/PCG64/integers",
        "runtime": f"{sys.version}; NumPy {np.__version__}",
        "state_cost_inputs": [o.result.cost.input_sha256 for o in outcomes],
    }
    digest = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    mean_use, pooled_use, mean_wait = _resource_summaries(
        outcomes,
        total,
        len(workload.cases),
    )
    return BatchUncertaintyResult(
        digest,
        recipe_digest,
        seed,
        f"{sys.version}; NumPy {np.__version__}",
        outcomes,
        indices,
        Fraction(feasible, total),
        mean_cost,
        RESOURCE_SUMMARY_VERSION,
        mean_use,
        pooled_use,
        mean_wait,
    )
