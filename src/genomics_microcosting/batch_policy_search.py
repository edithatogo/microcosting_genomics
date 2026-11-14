# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Finite assumed batch-policy comparisons with fixed process constraints."""

import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256
from typing import Literal, TypedDict, Unpack

from genomics_microcosting.dynamic_batch import DynamicBatchPolicy
from genomics_microcosting.static_batch_cost import (
    BatchPricing,
    DynamicBatchCost,
    calculate_dynamic_batch_cost,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.compute_cost import ComputeCostContext

MAX_POLICY_POINTS = 256


class PolicyGrid(TypedDict):
    """Payload and waiting-time choices for the finite policy search."""

    payload_limits: tuple[int, ...]
    max_wait_seconds: tuple[Decimal, ...]


def _valid_wait(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= 0


@dataclass(frozen=True)
class PolicyPoint:
    """Retain one policy, all modeled costs and its maximum served-case TAT."""

    policy: DynamicBatchPolicy
    result: DynamicBatchCost
    worst_turnaround_seconds: Decimal | None


@dataclass(frozen=True)
class PolicySearch:
    """Report finite-set nondominance with infeasible and idle points retained."""

    input_sha256: str
    points: tuple[PolicyPoint, ...]
    pareto_indices: tuple[int, ...]
    state: Literal["feasible", "infeasible", "no_demand"]


def _dominated(point: PolicyPoint, other: PolicyPoint) -> bool:
    tat, other_tat = point.worst_turnaround_seconds, other.worst_turnaround_seconds
    if tat is None or other_tat is None:
        return False
    cost, other_cost = point.result.cost.total_cost, other.result.cost.total_cost
    return (
        other_cost <= cost
        and other_tat <= tat
        and (other_cost < cost or other_tat < tat)
    )


def enumerate_batch_policies(
    workload: Workload,
    base_policy: DynamicBatchPolicy,
    pricing: BatchPricing,
    context: ComputeCostContext,
    **grid: Unpack[PolicyGrid],
) -> PolicySearch:
    """Enumerate at most 256 payload/wait choices with all other fields frozen.

    The base payload limit is the declared upper bound. Choices are assumptions,
    not inferred validated limits. Dominance minimizes total modeled cost and
    worst TAT only among completely served, temporally feasible policies.
    """
    if grid.keys() != PolicyGrid.__required_keys__:
        message = "Expected exactly payload_limits and max_wait_seconds"
        raise TypeError(message)
    payload_limits = grid["payload_limits"]
    max_wait_seconds = grid["max_wait_seconds"]
    workload = Workload.model_validate(workload.model_dump())
    base_policy = DynamicBatchPolicy.model_validate(base_policy.model_dump())
    pricing = BatchPricing.model_validate(pricing.model_dump())
    if (
        not payload_limits
        or not max_wait_seconds
        or len(payload_limits) * len(max_wait_seconds) > MAX_POLICY_POINTS
        or any(
            type(n) is not int or not 1 <= n <= base_policy.batch.payload_limit
            for n in payload_limits
        )
        or any(not _valid_wait(t) for t in max_wait_seconds)
        or len(set(payload_limits)) != len(payload_limits)
        or len(set(max_wait_seconds)) != len(max_wait_seconds)
    ):
        msg = "Invalid or excessive policy grid"
        raise ValueError(msg)
    arrivals = {case.case_id: case.arrival_seconds for case in workload.cases}
    points: list[PolicyPoint] = []
    for payload in payload_limits:
        for wait in max_wait_seconds:
            choice = sha256(
                json.dumps(
                    {
                        "base": base_policy.model_dump(mode="json"),
                        "payload_limit": payload,
                        "max_wait_seconds": str(wait),
                    },
                    sort_keys=True,
                ).encode(),
            ).hexdigest()
            policy = base_policy.model_copy(
                update={
                    "batch": base_policy.batch.model_copy(
                        update={
                            "payload_limit": payload,
                            "policy_id": (
                                f"{base_policy.batch.policy_id}/choice-{choice}"
                            ),
                        },
                    ),
                    "max_wait_seconds": wait,
                },
            )
            result = calculate_dynamic_batch_cost(workload, policy, pricing, context)
            turnaround: list[Decimal] = []
            with localcontext() as arithmetic:
                arithmetic.prec = 50
                arithmetic.traps[Inexact] = True
                for run in result.schedule.runs:
                    for case_id in run.case_ids:
                        arrival = arrivals[case_id]
                        if arrival is None:
                            msg = "Scheduled case has no arrival"
                            raise ValueError(msg)
                        turnaround.append(run.complete_seconds - arrival)
            points.append(PolicyPoint(policy, result, max(turnaround, default=None)))
    feasible = tuple(
        i
        for i, point in enumerate(points)
        if point.result.schedule.feasibility == "feasible"
        and point.worst_turnaround_seconds is not None
    )
    frontier = tuple(
        i
        for i in feasible
        if not any(_dominated(points[i], points[j]) for j in feasible)
    )
    identity = {
        "format_version": "batch-policy-search-v1",
        "cost_inputs": [p.result.cost.input_sha256 for p in points],
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return PolicySearch(
        digest,
        tuple(points),
        frontier,
        "no_demand" if not workload.cases else "feasible" if feasible else "infeasible",
    )
