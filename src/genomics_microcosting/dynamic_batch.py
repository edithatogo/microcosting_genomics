# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Deterministic assumed single-resource batching; no native scheduling or costs."""

import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.static_batch import StaticBatchPolicy, validate_batch_demand
from genomics_microcosting.workload_contract import Workload


class AvailabilityWindow(BaseModel):
    """Declare one uninterrupted availability interval in workload seconds."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    start_seconds: Decimal = Field(ge=0, allow_inf_nan=False)
    end_seconds: Decimal = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        """Require a positive window duration."""
        if self.start_seconds >= self.end_seconds:
            msg = "Availability window must have positive duration"
            raise ValueError(msg)
        return self


class DynamicBatchPolicy(BaseModel):
    """Declare constant run duration and full-or-timeout release assumptions."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )
    format_version: Literal["dynamic-batch-v1"] = "dynamic-batch-v1"
    batch: StaticBatchPolicy
    run_duration_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    max_wait_seconds: Decimal = Field(ge=0, allow_inf_nan=False)
    turnaround_limit_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    windows: tuple[AvailabilityWindow, ...]

    @model_validator(mode="after")
    def single_resource(self) -> Self:
        """Require requested-test timing and disjoint ordered windows."""
        if self.batch.entity_kind != "requested_tests":
            msg = "Dynamic arrival mapping supports requested tests only"
            raise ValueError(msg)
        for previous, current in zip(self.windows, self.windows[1:], strict=False):
            if current.start_seconds < previous.end_seconds:
                msg = "Availability windows overlap or are unordered"
                raise ValueError(msg)
        return self


@dataclass(frozen=True)
class ScheduledRun:
    """Retain one planned batch and its explicit control-slot consumption."""

    start_seconds: Decimal
    complete_seconds: Decimal
    case_ids: tuple[str, ...]
    control_slots: int


@dataclass(frozen=True)
class DynamicBatchResult:
    """Retain served, unserved and late work without discarding infeasibility."""

    input_sha256: str
    runs: tuple[ScheduledRun, ...]
    unserved_case_ids: tuple[str, ...]
    turnaround_violations: tuple[str, ...]
    feasibility: Literal["feasible", "infeasible"]
    termination_reason: Literal["completed", "availability_exhausted", "run_bound"]


def _window_start(release: Decimal, policy: DynamicBatchPolicy) -> Decimal | None:
    for window in policy.windows:
        start = max(release, window.start_seconds)
        if start + policy.run_duration_seconds <= window.end_seconds:
            return start
    return None


def earliest_batch_start(
    release: Decimal,
    policy: DynamicBatchPolicy,
) -> Decimal | None:
    """Find a start for one uninterrupted run in a validated calendar."""
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    if not release.is_finite() or release < 0:
        msg = "Batch release time must be finite and nonnegative"
        raise ValueError(msg)
    return _window_start(release, policy)


def schedule_batches(
    workload: Workload,
    policy: DynamicBatchPolicy,
) -> DynamicBatchResult:
    """Schedule deterministic FIFO full-or-timeout runs on one assumed resource."""
    workload = Workload.model_validate(workload.model_dump())
    policy = DynamicBatchPolicy.model_validate(policy.model_dump())
    validate_batch_demand(workload, policy.batch)
    if any(w.end_seconds > workload.horizon_seconds for w in policy.windows):
        msg = "Availability window exceeds workload horizon"
        raise ValueError(msg)
    pending: list[tuple[Decimal, str]] = []
    for case in workload.cases:
        if case.arrival_seconds is None:
            msg = "Dynamic scheduling requires explicit arrival times"
            raise ValueError(msg)
        pending.append((case.arrival_seconds, case.case_id))
    pending.sort()
    runs: list[ScheduledRun] = []
    late: list[str] = []
    ready = Decimal(0)
    with localcontext() as context:
        context.prec = 50
        context.traps[Inexact] = True
        while pending and len(runs) < policy.batch.max_runs:
            timeout = pending[0][0] + policy.max_wait_seconds
            full = (
                pending[policy.batch.payload_limit - 1][0]
                if len(pending) >= policy.batch.payload_limit
                else timeout
            )
            release = max(ready, min(timeout, full))
            start = _window_start(release, policy)
            if start is None:
                break
            selected = [
                item
                for item in pending[: policy.batch.payload_limit]
                if item[0] <= start
            ]
            complete = start + policy.run_duration_seconds
            runs.append(
                ScheduledRun(
                    start,
                    complete,
                    tuple(case_id for _, case_id in selected),
                    policy.batch.controls_per_run,
                ),
            )
            late.extend(
                case_id
                for arrival, case_id in selected
                if complete - arrival > policy.turnaround_limit_seconds
            )
            pending = pending[len(selected) :]
            ready = complete
    unserved = tuple(case_id for _, case_id in pending)
    termination: Literal["completed", "availability_exhausted", "run_bound"] = (
        "run_bound"
        if pending and len(runs) >= policy.batch.max_runs
        else "availability_exhausted"
        if pending
        else "completed"
    )
    identity = {
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return DynamicBatchResult(
        digest,
        tuple(runs),
        unserved,
        tuple(late),
        "infeasible" if unserved or late else "feasible",
        termination,
    )
