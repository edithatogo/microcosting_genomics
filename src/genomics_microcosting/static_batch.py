# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Opt-in assumed static capacity accounting; no timing or cost feasibility."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class StaticBatchPolicy(BaseModel):
    """Declare a single-assay homogeneous-slot planning assumption explicitly."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    policy_id: NonEmpty
    format_version: Literal["static-batch-v1"] = "static-batch-v1"
    process_id: NonEmpty
    assay_id: NonEmpty
    entity_kind: Literal["libraries", "specimens", "requested_tests"]
    capacity: int = Field(strict=True, gt=0)
    controls_per_run: int = Field(strict=True, ge=0)
    payload_limit: int = Field(strict=True, gt=0)
    max_runs: int = Field(strict=True, gt=0, le=10000)
    assumption_basis: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"

    @model_validator(mode="after")
    def physical_slots(self) -> Self:
        """Require controls and payload to fit the declared physical capacity."""
        if self.payload_limit + self.controls_per_run > self.capacity:
            msg = "Payload and controls exceed capacity"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class StaticBatchPlan:
    """Account for payload, controls and unused slots under explicit assumptions."""

    workload_id: str
    policy_id: str
    input_sha256: str
    payloads: tuple[int, ...]
    control_slots: int
    occupied_slots: int
    available_slots: int
    unused_slots: int
    time_feasibility: Literal["not_assessed"] = "not_assessed"


def validate_batch_demand(
    workload: Workload,
    policy: StaticBatchPolicy,
) -> int:
    """Validate common planning scope without requiring complete static service."""
    workload = Workload.model_validate(workload.model_dump())
    policy = StaticBatchPolicy.model_validate(policy.model_dump())
    if workload.process_id != policy.process_id:
        msg = "Workload and policy process differ"
        raise ValueError(msg)
    if workload.attempts != () or workload.control_ids != ():
        msg = "Static planning requires explicit empty prior attempts and controls"
        raise ValueError(msg)
    if any(case.assay_id != policy.assay_id for case in workload.cases):
        msg = "Workload assay differs from the single-assay policy"
        raise ValueError(msg)
    demand = workload.entity_counts()[policy.entity_kind]
    if demand is None:
        msg = "Workload demand mapping is unknown"
        raise ValueError(msg)
    return demand


def plan_static_batches(
    workload: Workload,
    policy: StaticBatchPolicy,
) -> StaticBatchPlan:
    """Pack known unattempted demand into bounded single-assay homogeneous runs."""
    workload = Workload.model_validate(workload.model_dump())
    policy = StaticBatchPolicy.model_validate(policy.model_dump())
    demand = validate_batch_demand(workload, policy)
    whole, remainder = divmod(demand, policy.payload_limit)
    runs = whole + bool(remainder)
    if runs > policy.max_runs:
        msg = "Static planning exceeds the explicit run bound"
        raise ValueError(msg)
    payloads = (policy.payload_limit,) * whole + ((remainder,) if remainder else ())
    controls = runs * policy.controls_per_run
    occupied = demand + controls
    available = runs * policy.capacity
    identity = {
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    return StaticBatchPlan(
        workload.workload_id,
        policy.policy_id,
        digest,
        payloads,
        controls,
        occupied,
        available,
        available - occupied,
    )
