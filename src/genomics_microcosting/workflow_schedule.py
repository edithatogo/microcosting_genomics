# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Schedule explicit assumed batches through a fixed shared-resource graph.

This offline heuristic never changes essential stages,
controls, assay compatibility or scripted outcomes to improve cost. Reservations
are allocated capacity-time, not measured consumption or paid labour. No native
scheduler, process activation, prices or clinical equivalence are implied.
"""

import json
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Literal, Self
lazy from collections.abc import Callable
lazy from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.parameter_provenance import (
    Digest,
    NonEmpty,
)
from genomics_microcosting.workload_contract import Workload
lazy from genomics_microcosting.dynamic_batch import AvailabilityWindow

ResourceKind = Literal["staff", "equipment", "compute", "storage", "licence"]
MAX_NUMERIC_DIGITS = 128


def _seconds(value: Decimal) -> Fraction:
    parts = value.as_tuple()
    if (
        not value.is_finite()
        or not isinstance(parts.exponent, int)
        or abs(parts.exponent) > MAX_NUMERIC_DIGITS
        or len(parts.digits) > MAX_NUMERIC_DIGITS
    ):
        msg = "Workflow time exceeds finite numeric profile bound"
        raise ValueError(msg)
    return Fraction(value)


class _Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )


class StageRole(_Model):
    """An essential role, independent of the selected resource pool."""

    role_id: NonEmpty
    kind: ResourceKind
    capacity_unit: NonEmpty


class WorkflowStage(_Model):
    """Freeze essential order, assay/slot and repeat constraints."""

    stage_id: NonEmpty
    predecessors: tuple[NonEmpty, ...]
    assay_ids: tuple[NonEmpty, ...] = Field(min_length=1)
    mixing_mode: Literal["homogeneous", "declared_compatible"]
    capacity: int = Field(strict=True, gt=0)
    payload_limit_bound: int = Field(strict=True, gt=0)
    controls_per_run: int = Field(strict=True, ge=0)
    max_attempts_per_case: int = Field(strict=True, gt=0, le=100)
    roles: tuple[StageRole, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def constraints(self) -> Self:
        """Reject duplicate graph declarations and impossible slot limits."""
        if (
            len(set(self.predecessors)) != len(self.predecessors)
            or len(set(self.assay_ids)) != len(self.assay_ids)
            or len({r.role_id for r in self.roles}) != len(self.roles)
            or self.payload_limit_bound + self.controls_per_run > self.capacity
        ):
            msg = "Invalid stage identities or payload/control capacity"
            raise ValueError(msg)
        return self


def _acyclic(dependencies: dict[str, set[str]]) -> None:
    remaining = {key: set(values) for key, values in dependencies.items()}
    while remaining:
        ready = {key for key, values in remaining.items() if not values}
        if not ready:
            msg = "Workflow dependency cycle or dangling dependency"
            raise ValueError(msg)
        remaining = {
            key: values - ready for key, values in remaining.items() if key not in ready
        }


class WorkflowGraph(_Model):
    """An explicitly assumed graph whose exact bytes are pinned by workload."""

    format_version: Literal["batch-process-graph-v1"]
    process_id: NonEmpty
    evidence_state: Literal["assumed"]
    assumption_basis: NonEmpty
    stages: tuple[WorkflowStage, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def graph_constraints(self) -> Self:
        """Require a DAG and every applicable case's predecessor closure."""
        stages = {s.stage_id: s for s in self.stages}
        if len(stages) != len(self.stages):
            msg = "Duplicate workflow stage"
            raise ValueError(msg)
        for stage in self.stages:
            for predecessor in stage.predecessors:
                if predecessor not in stages or not set(stage.assay_ids) <= set(
                    stages[predecessor].assay_ids,
                ):
                    msg = "Stage predecessor/assay applicability is incomplete"
                    raise ValueError(msg)
        _acyclic({s.stage_id: set(s.predecessors) for s in self.stages})
        return self


class ResourcePool(_Model):
    """A shared constant-capacity pool with explicit uninterrupted windows."""

    resource_id: NonEmpty
    kind: ResourceKind
    capacity_unit: NonEmpty
    capacity: int = Field(strict=True, gt=0)
    windows: tuple[AvailabilityWindow, ...]

    @model_validator(mode="after")
    def window_order(self) -> Self:
        """Reject overlapping or unordered resource calendars."""
        for previous, current in zip(
            self.windows,
            self.windows[1:],
            strict=False,
        ):
            if current.start_seconds < previous.end_seconds:
                msg = "Resource windows overlap or are unordered"
                raise ValueError(msg)
        return self


class ResourceNeed(_Model):
    """Reserve one role for an explicit offset/duration within a run."""

    role_id: NonEmpty
    resource_id: NonEmpty
    units: int = Field(strict=True, gt=0)
    offset_seconds: Decimal = Field(ge=0, allow_inf_nan=False)
    duration_seconds: Decimal = Field(gt=0, allow_inf_nan=False)


class StageTiming(_Model):
    """Declare assumed constant run timing, separating hands-on phases."""

    stage_id: NonEmpty
    duration_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    needs: tuple[ResourceNeed, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def enclosed_roles(self) -> Self:
        """Every role fits within the constant run and occurs exactly once."""
        duration = _seconds(self.duration_seconds)
        if len({n.role_id for n in self.needs}) != len(self.needs) or any(
            _seconds(n.offset_seconds) + _seconds(n.duration_seconds) > duration
            for n in self.needs
        ):
            msg = "Role timing is repeated or exceeds run duration"
            raise ValueError(msg)
        return self


class ResourceSchedulePolicy(_Model):
    """Bind calendars and timing without rewriting the frozen clinical graph."""

    format_version: Literal["resource-schedule-v1"]
    policy_id: NonEmpty
    evidence_state: Literal["assumed"] = "assumed"
    assumption_basis: NonEmpty
    process_graph_sha256: Digest
    parameter_version_id: NonEmpty
    turnaround_limit_seconds: Decimal = Field(gt=0, allow_inf_nan=False)
    max_operations: int = Field(strict=True, gt=0, le=256)
    resources: tuple[ResourcePool, ...] = Field(min_length=1, max_length=32)
    timings: tuple[StageTiming, ...] = Field(min_length=1, max_length=32)


class PlannedMember(_Model):
    """One future case/stage attempt and an explicitly scripted outcome."""

    case_id: NonEmpty
    ordinal: int = Field(strict=True, gt=0)
    outcome: Literal["passed", "failed"]


class PlannedOperation(_Model):
    """An explicit batch grouping with declared assay compatibility."""

    operation_id: NonEmpty
    stage_id: NonEmpty
    members: tuple[PlannedMember, ...] = Field(min_length=1)
    release_seconds: Decimal = Field(ge=0, allow_inf_nan=False)
    dependencies: tuple[NonEmpty, ...]


class CaseCancellation(_Model):
    """Cancel future service while retaining active reservations."""

    case_id: NonEmpty
    at_seconds: Decimal = Field(ge=0, allow_inf_nan=False)


class WorkflowScenario(_Model):
    """Retain proposed grouping, failures/rework and cancellation assertions."""

    scenario_id: NonEmpty
    parameter_version_id: NonEmpty
    evidence_state: Literal["assumed"]
    assumption_basis: NonEmpty
    operations: tuple[PlannedOperation, ...] = Field(max_length=1024)
    cancellations: tuple[CaseCancellation, ...]


@dataclass(frozen=True)
class ResourceReservation:
    """Half-open allocated occupation with no consumption inference."""

    operation_id: str
    role_id: str
    resource_id: str
    units: int
    start_seconds: Fraction
    complete_seconds: Fraction


@dataclass(frozen=True)
class WorkflowRun:
    """Preserve actual modeled members, controls and release/service times."""

    operation_id: str
    stage_id: str
    members: tuple[PlannedMember, ...]
    ready_seconds: Fraction
    start_seconds: Fraction
    complete_seconds: Fraction
    control_slots: int
    unused_slots: int


@dataclass(frozen=True)
class WorkflowCaseResult:
    """Preserve completed, failed, cancelled and unserved requested tests."""

    case_id: str
    state: Literal["completed", "failed", "cancelled", "unserved"]
    complete_seconds: Fraction | None
    turnaround_seconds: Fraction | None
    turnaround_violation: bool


@dataclass(frozen=True)
class ResourceUtilization:
    """Reconcile available, allocated and idle capacity-time."""

    resource_id: str
    kind: ResourceKind
    capacity_unit: str
    available_unit_seconds: Fraction
    allocated_unit_seconds: Fraction
    idle_unit_seconds: Fraction
    utilization_fraction: Fraction | None


@dataclass(frozen=True)
class WorkflowSchedule:
    """An offline result retaining residual work and feasibility."""

    input_sha256: str
    workload_id: str
    process_id: str
    process_graph_sha256: str
    parameter_version_id: str
    policy_id: str
    scenario_id: str
    runs: tuple[WorkflowRun, ...]
    reservations: tuple[ResourceReservation, ...]
    skipped_operation_ids: tuple[str, ...]
    unserved_operation_ids: tuple[str, ...]
    cases: tuple[WorkflowCaseResult, ...]
    resources: tuple[ResourceUtilization, ...]
    feasibility: Literal["feasible", "infeasible"]
    termination_reason: Literal[
        "completed",
        "availability_exhausted",
        "operation_bound",
    ]


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate workflow graph JSON field"
            raise ValueError(msg)
        result[key] = value
    return result


def _validate_resources(
    graph: WorkflowGraph,
    workload: Workload,
    policy: ResourceSchedulePolicy,
) -> None:
    resources = {r.resource_id: r for r in policy.resources}
    timings = {t.stage_id: t for t in policy.timings}
    if (
        len(resources) != len(policy.resources)
        or len(timings) != len(policy.timings)
        or timings.keys() != {s.stage_id for s in graph.stages}
    ):
        msg = "Resource/timing IDs repeat or stage coverage differs"
        raise ValueError(msg)
    for resource in policy.resources:
        for window in resource.windows:
            _seconds(window.start_seconds)
            if _seconds(window.end_seconds) > _seconds(
                workload.horizon_seconds,
            ):
                msg = "Resource window exceeds workload horizon"
                raise ValueError(msg)
    for stage in graph.stages:
        roles = {r.role_id: (r.kind, r.capacity_unit) for r in stage.roles}
        timing = timings[stage.stage_id]
        if roles.keys() != {n.role_id for n in timing.needs}:
            msg = "Essential resource role coverage differs"
            raise ValueError(msg)
        for need in timing.needs:
            if (
                need.resource_id not in resources
                or (
                    resources[need.resource_id].kind,
                    resources[need.resource_id].capacity_unit,
                )
                != roles[need.role_id]
            ):
                msg = "Resource kind/unit differs from essential graph role"
                raise ValueError(msg)


def _histories(
    graph: WorkflowGraph,
    workload: Workload,
    scenario: WorkflowScenario,
) -> dict[tuple[str, str], list[tuple[PlannedOperation, PlannedMember]]]:
    cases = {c.case_id: c for c in workload.cases}
    stages = {s.stage_id: s for s in graph.stages}
    histories: dict[
        tuple[str, str],
        list[tuple[PlannedOperation, PlannedMember]],
    ] = {}
    ids = {op.operation_id for op in scenario.operations}
    if len(ids) != len(scenario.operations):
        msg = "Duplicate operation identity"
        raise ValueError(msg)
    for op in scenario.operations:
        _seconds(op.release_seconds)
        if op.stage_id not in stages:
            msg = "Unknown operation stage"
            raise ValueError(msg)
        stage = stages[op.stage_id]
        members = {m.case_id for m in op.members}
        if (
            len(members) != len(op.members)
            or len(op.members) > stage.payload_limit_bound
        ):
            msg = "Duplicate case or excessive batch payload"
            raise ValueError(msg)
        if not members <= cases.keys() or any(
            cases[m.case_id].assay_id not in stage.assay_ids for m in op.members
        ):
            msg = "Case/assay is outside the fixed stage graph"
            raise ValueError(msg)
        if (
            stage.mixing_mode == "homogeneous"
            and len(
                {cases[m.case_id].assay_id for m in op.members},
            )
            != 1
        ):
            msg = "Assay mixing is not allowed by the graph"
            raise ValueError(msg)
        for member in op.members:
            histories.setdefault((member.case_id, op.stage_id), []).append(
                (op, member),
            )
    for (_, stage_id), history in histories.items():
        history.sort(key=lambda pair: pair[1].ordinal)
        if (
            [m.ordinal for _, m in history] != list(range(1, len(history) + 1))
            or len(history) > stages[stage_id].max_attempts_per_case
            or any(m.outcome != "failed" for _, m in history[:-1])
        ):
            msg = "Invalid stage attempt history or repeat limit"
            raise ValueError(msg)
    return histories


def _validate_stage_coverage(
    graph: WorkflowGraph,
    workload: Workload,
    scenario: WorkflowScenario,
    histories: dict[
        tuple[str, str],
        list[tuple[PlannedOperation, PlannedMember]],
    ],
) -> None:
    cases = {c.case_id for c in workload.cases}
    cancelled = {
        c.case_id
        for c in scenario.cancellations
        if _seconds(c.at_seconds) <= _seconds(workload.horizon_seconds)
    }
    if any(c.case_id not in cases for c in scenario.cancellations) or len(
        {c.case_id for c in scenario.cancellations},
    ) != len(scenario.cancellations):
        msg = "Cancellation identities are unknown or duplicated"
        raise ValueError(msg)
    for case in workload.cases:
        failed = {
            stage
            for (case_id, stage), h in histories.items()
            if case_id == case.case_id and h[-1][1].outcome == "failed"
        }
        blocked = set(failed)
        while True:
            expanded = blocked | {
                s.stage_id for s in graph.stages if set(s.predecessors) & blocked
            }
            if expanded == blocked:
                break
            blocked = expanded
        for stage in graph.stages:
            if (
                case.assay_id in stage.assay_ids
                and (case.case_id, stage.stage_id) not in histories
                and stage.stage_id not in blocked
                and case.case_id not in cancelled
            ):
                msg = "Required case/stage coverage is incomplete"
                raise ValueError(msg)


def _validate_operations(
    graph: WorkflowGraph,
    workload: Workload,
    scenario: WorkflowScenario,
) -> dict[tuple[str, str], list[tuple[PlannedOperation, PlannedMember]]]:
    histories = _histories(graph, workload, scenario)
    stages = {s.stage_id: s for s in graph.stages}
    _validate_stage_coverage(graph, workload, scenario, histories)
    for op in scenario.operations:
        required: set[str] = set()
        for member in op.members:
            if member.ordinal > 1:
                prior = histories[(member.case_id, op.stage_id)][member.ordinal - 2]
                required.add(prior[0].operation_id)
            for stage_id in stages[op.stage_id].predecessors:
                history = histories.get((member.case_id, stage_id))
                if history is None or history[-1][1].outcome != "passed":
                    msg = "Downstream operation has no passed predecessor"
                    raise ValueError(msg)
                required.add(history[-1][0].operation_id)
        if set(op.dependencies) != required or len(op.dependencies) != len(
            required,
        ):
            msg = "Operation dependencies differ from fixed graph/attempts"
            raise ValueError(msg)
    _acyclic({o.operation_id: set(o.dependencies) for o in scenario.operations})
    return histories


def _reservations(
    op_id: str,
    timing: StageTiming,
    start: Fraction,
) -> tuple[ResourceReservation, ...]:
    return tuple(
        ResourceReservation(
            op_id,
            n.role_id,
            n.resource_id,
            n.units,
            start + _seconds(n.offset_seconds),
            start + _seconds(n.offset_seconds) + _seconds(n.duration_seconds),
        )
        for n in timing.needs
    )


def _fits(
    proposed: tuple[ResourceReservation, ...],
    existing: list[ResourceReservation],
    pools: dict[str, ResourcePool],
) -> bool:
    for resource_id in {r.resource_id for r in proposed}:
        pool = pools[resource_id]
        current = [r for r in proposed if r.resource_id == resource_id]
        for claim in current:
            if not any(
                _seconds(w.start_seconds) <= claim.start_seconds
                and claim.complete_seconds <= _seconds(w.end_seconds)
                for w in pool.windows
            ):
                return False
        all_claims = [r for r in existing if r.resource_id == resource_id] + current
        knots = {t for r in all_claims for t in (r.start_seconds, r.complete_seconds)}
        for tick in knots:
            if any(r.start_seconds <= tick < r.complete_seconds for r in current):
                used = sum(
                    r.units
                    for r in all_claims
                    if r.start_seconds <= tick < r.complete_seconds
                )
                if used > pool.capacity:
                    return False
    return True


def _earliest(
    ready: Fraction,
    timing: StageTiming,
    existing: list[ResourceReservation],
    policy: ResourceSchedulePolicy,
    horizon: Fraction,
) -> Fraction | None:
    pools = {r.resource_id: r for r in policy.resources}
    candidates = {ready}
    for need in timing.needs:
        offset = _seconds(need.offset_seconds)
        candidates.update(
            _seconds(w.start_seconds) - offset for w in pools[need.resource_id].windows
        )
        candidates.update(
            r.complete_seconds - offset
            for r in existing
            if r.resource_id == need.resource_id
        )
    for start in sorted(candidates):
        if (
            ready <= start
            and start + _seconds(timing.duration_seconds) <= horizon
            and _fits(
                _reservations("candidate", timing, start),
                existing,
                pools,
            )
        ):
            return start
    return None


def _case_results(
    workload: Workload,
    graph: WorkflowGraph,
    scenario: WorkflowScenario,
    runs: tuple[WorkflowRun, ...],
    policy: ResourceSchedulePolicy,
) -> tuple[WorkflowCaseResult, ...]:
    cancellations = {c.case_id: _seconds(c.at_seconds) for c in scenario.cancellations}
    history: dict[tuple[str, str], list[tuple[Fraction, PlannedMember]]] = {}
    for run in runs:
        for member in run.members:
            history.setdefault((member.case_id, run.stage_id), []).append(
                (run.complete_seconds, member),
            )
    planned: dict[tuple[str, str], int] = {}
    for operation in scenario.operations:
        for member in operation.members:
            key = (member.case_id, operation.stage_id)
            planned[key] = max(planned.get(key, 0), member.ordinal)
    results: list[WorkflowCaseResult] = []
    for case in workload.cases:
        required = [s.stage_id for s in graph.stages if case.assay_id in s.assay_ids]
        last = {
            s: max(history[(case.case_id, s)], key=lambda pair: pair[1].ordinal)
            for s in required
            if (case.case_id, s) in history
        }
        passed = len(last) == len(required) and all(
            m.outcome == "passed" and m.ordinal == planned[(case.case_id, s)]
            for s, (_, m) in last.items()
        )
        complete = max((t for t, _ in last.values()), default=Fraction(0))
        cancel = cancellations.get(case.case_id)
        state: Literal["completed", "failed", "cancelled", "unserved"] = "unserved"
        if passed and (cancel is None or complete < cancel):
            state = "completed"
        elif cancel is not None and cancel <= _seconds(
            workload.horizon_seconds,
        ):
            state = "cancelled"
        elif any(
            m.outcome == "failed" and m.ordinal == planned[(case.case_id, s)]
            for s, (_, m) in last.items()
        ):
            state = "failed"
        turnaround = (
            complete - _seconds(case.arrival_seconds)
            if state == "completed" and case.arrival_seconds is not None
            else None
        )
        results.append(
            WorkflowCaseResult(
                case.case_id,
                state,
                complete if state == "completed" else None,
                turnaround,
                turnaround is not None
                and turnaround > _seconds(policy.turnaround_limit_seconds),
            ),
        )
    return tuple(results)


def _utilization(
    policy: ResourceSchedulePolicy,
    claims: tuple[ResourceReservation, ...],
) -> tuple[ResourceUtilization, ...]:
    results: list[ResourceUtilization] = []
    for resource in policy.resources:
        available = resource.capacity * sum(
            (
                _seconds(w.end_seconds) - _seconds(w.start_seconds)
                for w in resource.windows
            ),
            Fraction(0),
        )
        used = sum(
            (
                r.units * (r.complete_seconds - r.start_seconds)
                for r in claims
                if r.resource_id == resource.resource_id
            ),
            Fraction(0),
        )
        results.append(
            ResourceUtilization(
                resource.resource_id,
                resource.kind,
                resource.capacity_unit,
                available,
                used,
                available - used,
                None if available == 0 else used / available,
            ),
        )
    return tuple(results)


@dataclass(frozen=True)
class _DispatchResult:
    runs: tuple[WorkflowRun, ...]
    reservations: tuple[ResourceReservation, ...]
    skipped: tuple[str, ...]
    pending: tuple[str, ...]
    completed_count: int


def _run_operations(
    graph: WorkflowGraph,
    workload: Workload,
    policy: ResourceSchedulePolicy,
    scenario: WorkflowScenario,
) -> _DispatchResult:
    horizon = _seconds(workload.horizon_seconds)
    stages = {s.stage_id: s for s in graph.stages}
    timings = {t.stage_id: t for t in policy.timings}
    arrivals = {
        c.case_id: _seconds(c.arrival_seconds)
        for c in workload.cases
        if c.arrival_seconds is not None
    }
    cancellations = {c.case_id: _seconds(c.at_seconds) for c in scenario.cancellations}
    pending = {o.operation_id: o for o in scenario.operations}
    done: dict[str, Fraction] = {}
    runs: list[WorkflowRun] = []
    claims: list[ResourceReservation] = []
    skipped: list[str] = []
    while pending and len(done) < policy.max_operations:
        choices: list[tuple[Fraction, str, Fraction, bool]] = []
        for op in pending.values():
            if all(m.case_id in cancellations for m in op.members):
                cancel_at = max(cancellations[m.case_id] for m in op.members)
                if cancel_at <= horizon:
                    choices.append(
                        (cancel_at, op.operation_id, cancel_at, True),
                    )
            if not set(op.dependencies) <= done.keys():
                continue
            ready = max(
                _seconds(op.release_seconds),
                *(
                    min(
                        arrivals[m.case_id],
                        cancellations.get(m.case_id, horizon + 1),
                    )
                    for m in op.members
                ),
                *(done[d] for d in op.dependencies),
            )
            start = _earliest(
                ready,
                timings[op.stage_id],
                claims,
                policy,
                horizon,
            )
            if start is not None:
                choices.append((start, op.operation_id, ready, False))
        if not choices:
            break
        start, op_id, ready, all_cancelled = min(choices)
        op = pending.pop(op_id)
        members = tuple(
            m for m in op.members if cancellations.get(m.case_id, horizon + 1) > start
        )
        if all_cancelled or not members:
            skipped.append(op_id)
            done[op_id] = start
            continue
        timing = timings[op.stage_id]
        complete = start + _seconds(timing.duration_seconds)
        stage = stages[op.stage_id]
        runs.append(
            WorkflowRun(
                op_id,
                op.stage_id,
                members,
                ready,
                start,
                complete,
                stage.controls_per_run,
                stage.capacity - len(members) - stage.controls_per_run,
            ),
        )
        claims.extend(_reservations(op_id, timing, start))
        done[op_id] = complete
    return _DispatchResult(
        tuple(runs),
        tuple(claims),
        tuple(skipped),
        tuple(sorted(pending)),
        len(done),
    )


def schedule_workflow(
    graph_payload: bytes,
    workload: Workload,
    policy: ResourceSchedulePolicy,
    scenario: WorkflowScenario,
) -> WorkflowSchedule:
    """Schedule fixed-graph batches using nonpreemptive resources.

    The serial schedule-generation rule commits the ready operation with the
    earliest feasible start, breaking ties by operation ID. It is not a solver
    or a proof of global optimality. Scripted outcomes are proposed assumptions.
    """
    return _schedule_workflow(
        graph_payload,
        workload,
        policy,
        scenario,
        _OperationContract(_validate_operations),
    )


@dataclass(frozen=True)
class _OperationContract:
    validate: Callable[[WorkflowGraph, Workload, WorkflowScenario], object]
    identity: dict[str, object] | None = None


def _schedule_workflow(
    graph_payload: bytes,
    workload: Workload,
    policy: ResourceSchedulePolicy,
    scenario: WorkflowScenario,
    operation_contract: _OperationContract,
) -> WorkflowSchedule:
    """Share resource dispatch after a version-specific operation validation."""
    workload = Workload.model_validate(workload)
    policy = ResourceSchedulePolicy.model_validate(policy)
    scenario = WorkflowScenario.model_validate(scenario)
    digest = sha256(graph_payload).hexdigest()
    if digest != workload.process_graph_sha256 or digest != policy.process_graph_sha256:
        msg = "Workflow graph hash differs from fixed workload/policy"
        raise ValueError(msg)
    graph = WorkflowGraph.model_validate(
        json.loads(graph_payload, object_pairs_hook=_unique_fields),
    )
    if (
        graph.process_id != workload.process_id
        or policy.parameter_version_id != workload.parameter_version_id
        or scenario.parameter_version_id != workload.parameter_version_id
    ):
        msg = "Workflow process/parameter identity mismatch"
        raise ValueError(msg)
    assays = {a for s in graph.stages for a in s.assay_ids}
    if (
        workload.attempts != ()
        or workload.control_ids != ()
        or any(
            c.arrival_seconds is None or c.assay_id not in assays
            for c in workload.cases
        )
    ):
        msg = "Workflow needs known arrivals/assays and empty prior histories"
        raise ValueError(msg)
    _seconds(workload.horizon_seconds)
    _seconds(policy.turnaround_limit_seconds)
    _validate_resources(graph, workload, policy)
    operation_contract.validate(graph, workload, scenario)
    execution = _run_operations(graph, workload, policy, scenario)
    cases = _case_results(workload, graph, scenario, execution.runs, policy)
    identity = {
        "graph_sha256": digest,
        "workload": workload.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
        "scenario": (
            scenario.model_dump(mode="json")
            if operation_contract.identity is None
            else operation_contract.identity
        ),
    }
    input_digest = sha256(
        json.dumps(identity, sort_keys=True).encode(),
    ).hexdigest()
    termination: Literal[
        "completed",
        "availability_exhausted",
        "operation_bound",
    ] = (
        "operation_bound"
        if execution.pending and execution.completed_count >= policy.max_operations
        else "availability_exhausted"
        if execution.pending
        else "completed"
    )
    return WorkflowSchedule(
        input_digest,
        workload.workload_id,
        workload.process_id,
        digest,
        workload.parameter_version_id,
        policy.policy_id,
        scenario.scenario_id,
        execution.runs,
        execution.reservations,
        execution.skipped,
        execution.pending,
        cases,
        _utilization(policy, execution.reservations),
        "feasible"
        if all(c.state == "completed" and not c.turnaround_violation for c in cases)
        and not execution.pending
        else "infeasible",
        termination,
    )


class ReworkMember(PlannedMember):
    """Bind an attempt to exact predecessor outputs and its repeat trigger."""

    input_operation_ids: tuple[NonEmpty, ...]
    rework_trigger_operation_id: NonEmpty | None


class ReworkOperation(_Model):
    """An explicit batch whose members retain individual input provenance."""

    operation_id: NonEmpty
    stage_id: NonEmpty
    release_seconds: Decimal = Field(ge=0, allow_inf_nan=False)
    dependencies: tuple[NonEmpty, ...]
    members: tuple[ReworkMember, ...] = Field(min_length=1)


class ReworkScenario(_Model):
    """Select bounded scripted rework without rewriting the essential DAG."""

    scenario_id: NonEmpty
    parameter_version_id: NonEmpty
    evidence_state: Literal["assumed"]
    assumption_basis: NonEmpty
    cancellations: tuple[CaseCancellation, ...]
    format_version: Literal["workflow-rework-v1"]
    operations: tuple[ReworkOperation, ...] = Field(max_length=1024)


def _compile_rework(scenario: ReworkScenario) -> WorkflowScenario:
    return WorkflowScenario.model_validate(
        {
            key: value
            for key, value in scenario.model_dump(
                exclude={"format_version"},
            ).items()
            if key != "operations"
        }
        | {
            "operations": tuple(
                PlannedOperation(
                    operation_id=op.operation_id,
                    stage_id=op.stage_id,
                    release_seconds=op.release_seconds,
                    dependencies=op.dependencies,
                    members=tuple(
                        PlannedMember(
                            case_id=m.case_id,
                            ordinal=m.ordinal,
                            outcome=m.outcome,
                        )
                        for m in op.members
                    ),
                )
                for op in scenario.operations
            ),
        },
    )


def _validate_rework(
    graph: WorkflowGraph,
    workload: Workload,
    scenario: ReworkScenario,
) -> None:
    """Validate every version, trigger, dependency and final input closure."""
    stages = {s.stage_id: s for s in graph.stages}
    cases = {c.case_id: c for c in workload.cases}
    operations = {op.operation_id: op for op in scenario.operations}
    if len(operations) != len(scenario.operations):
        msg = "Duplicate rework operation identity"
        raise ValueError(msg)
    histories: dict[tuple[str, str], list[tuple[ReworkOperation, ReworkMember]]] = {}
    members: dict[tuple[str, str], ReworkMember] = {}
    for op in scenario.operations:
        _seconds(op.release_seconds)
        stage = stages.get(op.stage_id)
        ids = {m.case_id for m in op.members}
        if (
            stage is None
            or len(ids) != len(op.members)
            or len(op.members) > stage.payload_limit_bound
            or not ids <= cases.keys()
            or any(cases[c].assay_id not in stage.assay_ids for c in ids)
            or (
                stage.mixing_mode == "homogeneous"
                and len({cases[c].assay_id for c in ids}) != 1
            )
        ):
            msg = "Invalid rework stage, members, assay or capacity"
            raise ValueError(msg)
        for member in op.members:
            histories.setdefault((member.case_id, op.stage_id), []).append(
                (op, member),
            )
            members[(op.operation_id, member.case_id)] = member
    for (_, stage_id), history in histories.items():
        history.sort(key=lambda pair: pair[1].ordinal)
        if [m.ordinal for _, m in history] != list(range(1, len(history) + 1)) or len(
            history,
        ) > stages[stage_id].max_attempts_per_case:
            msg = "Invalid rework attempt order or repeat bound"
            raise ValueError(msg)
    _validate_inputs(stages, operations, histories, members)
    plain = _compile_rework(scenario)
    plain_operations = {o.operation_id: o for o in plain.operations}
    plain_histories = {
        key: [
            (
                plain_operations[op.operation_id],
                PlannedMember(case_id=m.case_id, ordinal=m.ordinal, outcome=m.outcome),
            )
            for op, m in history
        ]
        for key, history in histories.items()
    }
    _validate_stage_coverage(graph, workload, plain, plain_histories)
    _acyclic({o.operation_id: set(o.dependencies) for o in scenario.operations})


def _validate_inputs(
    stages: dict[str, WorkflowStage],
    operations: dict[str, ReworkOperation],
    histories: dict[tuple[str, str], list[tuple[ReworkOperation, ReworkMember]]],
    members: dict[tuple[str, str], ReworkMember],
) -> None:
    """Require exact graph inputs and causal downstream repeat triggers."""
    for op in operations.values():
        required: set[str] = set()
        for member in op.members:
            inputs = member.input_operation_ids
            producers = [operations.get(i) for i in inputs]
            if (
                len(set(inputs)) != len(inputs)
                or any(p is None for p in producers)
                or {p.stage_id for p in producers if p is not None}
                != set(stages[op.stage_id].predecessors)
                or len(inputs) != len(stages[op.stage_id].predecessors)
                or any(
                    (i, member.case_id) not in members
                    or members[(i, member.case_id)].outcome != "passed"
                    for i in inputs
                )
            ):
                msg = "Rework input coverage requires passed same-case predecessors"
                raise ValueError(msg)
            history = histories[(member.case_id, op.stage_id)]
            if member.ordinal == len(history):
                for producer in producers:
                    if (
                        producer is not None
                        and histories[(member.case_id, producer.stage_id)][-1][
                            0
                        ].operation_id
                        != producer.operation_id
                    ):
                        msg = "Final rework output consumes a stale predecessor"
                        raise ValueError(msg)
            required.update(inputs)
            required.update(
                _repeat_dependencies(member, history, operations, members),
            )
        if len(op.dependencies) != len(required) or set(op.dependencies) != required:
            msg = "Rework dependencies differ from inputs, retries or triggers"
            raise ValueError(msg)


def _repeat_dependencies(
    member: ReworkMember,
    history: list[tuple[ReworkOperation, ReworkMember]],
    operations: dict[str, ReworkOperation],
    members: dict[tuple[str, str], ReworkMember],
) -> set[str]:
    """Retain same-stage ordering and justify repeats of passed work."""
    trigger = member.rework_trigger_operation_id
    if member.ordinal == 1:
        if trigger is not None:
            msg = "First attempt cannot declare a rework trigger"
            raise ValueError(msg)
        return set()
    previous, prior = history[member.ordinal - 2]
    required = {previous.operation_id}
    if prior.outcome == "failed":
        if trigger is not None:
            msg = "Failed same-stage retry cannot add a rework trigger"
            raise ValueError(msg)
        return required
    if (
        trigger is None
        or (trigger, member.case_id) not in members
        or members[(trigger, member.case_id)].outcome != "failed"
        or operations[trigger].stage_id == previous.stage_id
        or not _consumes(trigger, member.case_id, previous.operation_id, members)
    ):
        msg = "Passed repeat needs a causally linked downstream failure"
        raise ValueError(msg)
    required.add(trigger)
    return required


def _consumes(
    operation_id: str,
    case_id: str,
    producer_id: str,
    members: dict[tuple[str, str], ReworkMember],
) -> bool:
    pending = [operation_id]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        member = members.get((current, case_id))
        if member is not None:
            if producer_id in member.input_operation_ids:
                return True
            pending.extend(member.input_operation_ids)
    return False


def schedule_workflow_rework(
    graph_payload: bytes,
    workload: Workload,
    policy: ResourceSchedulePolicy,
    scenario: ReworkScenario,
) -> WorkflowSchedule:
    """Schedule explicitly linked rework with all original resource guards.

    Args:
        graph_payload: Unchanged exact essential stage DAG bytes.
        workload: Fixed cases, assays, arrivals and horizon.
        policy: Shared calendars, timing, turnaround and operation bound.
        scenario: Explicit assumed attempts, input versions and failure links.

    Returns:
        Complete reservations, controls, failed/repeated work and final service.

    Raises:
        ValueError: Invalid source identity, graph, inputs, triggers or limits.

    """
    scenario = ReworkScenario.model_validate(scenario)

    def validate(
        graph: WorkflowGraph,
        current: Workload,
        _: WorkflowScenario,
    ) -> None:
        _validate_rework(graph, current, scenario)

    return _schedule_workflow(
        graph_payload,
        workload,
        policy,
        _compile_rework(scenario),
        _OperationContract(validate, scenario.model_dump(mode="json")),
    )
