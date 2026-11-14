# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Draft resource arithmetic; this module does not qualify real comparisons.

Source validity, clinical equivalence and completeness must be established by a
separate integration. Inputs are explicit and unknowns cannot become zero.
"""

from decimal import Decimal, Inexact, InvalidOperation, localcontext
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genomics_microcosting.provenance_ledger import Parameter, ParameterSet
lazy from genomics_microcosting.parameter_provenance import NonEmpty


class ResourceLine(BaseModel):
    """One explicitly measured or assumed resource cost per functional unit."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    resource_id: NonEmpty
    quantity: Decimal = Field(ge=0, allow_inf_nan=False)
    quantity_unit: NonEmpty
    unit_cost: Decimal = Field(ge=0, allow_inf_nan=False)
    cost_denominator_unit: NonEmpty
    currency: NonEmpty
    allocation: Decimal = Field(ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def matching_units(self) -> Self:
        """Reject implicit conversions and denominator mismatches."""
        if self.quantity_unit != self.cost_denominator_unit:
            msg = "Resource quantity and price denominator units differ"
            raise ValueError(msg)
        return self

    def cost(self) -> Decimal:
        """Return an unrounded allocated line cost."""
        checked = ResourceLine.model_validate(self.model_dump())
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.traps[Inexact] = True
            return checked.quantity * checked.unit_cost * checked.allocation


class BaselineDisposition(BaseModel):
    """Account explicitly for one baseline resource in the proposed alternative."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    baseline_resource_id: NonEmpty
    action: Literal["retained", "removed", "replaced", "stranded"]
    candidate_resource_ids: tuple[NonEmpty, ...]
    residual_treatment: Literal["none", "stranded"]
    stranded_resource_ids: tuple[NonEmpty, ...]

    @model_validator(mode="after")
    def valid_mapping(self) -> Self:
        """Require an explicit mapping for every resource that remains in use."""
        all_ids = (*self.candidate_resource_ids, *self.stranded_resource_ids)
        if len(set(all_ids)) != len(all_ids):
            msg = "Duplicate candidate resource mapping"
            raise ValueError(msg)
        no_operational_use = self.action in {"removed", "stranded"}
        if no_operational_use != (not self.candidate_resource_ids):
            msg = "Removed and stranded resources have no operational mapping"
            raise ValueError(msg)
        if (self.residual_treatment == "stranded") != bool(self.stranded_resource_ids):
            msg = "Stranded treatment and stranded resource mapping differ"
            raise ValueError(msg)
        if self.action == "stranded" and self.residual_treatment != "stranded":
            msg = "Stranded action requires stranded treatment"
            raise ValueError(msg)
        if self.action == "retained" and self.residual_treatment != "none":
            msg = "Retained action cannot add a stranded residual"
            raise ValueError(msg)
        return self


class DraftResourceComparison(BaseModel):
    """Describe accounting inputs without asserting provenance or equivalence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    baseline: tuple[ResourceLine, ...]
    candidate: tuple[ResourceLine, ...]
    dispositions: tuple[BaselineDisposition, ...]
    added_candidate_ids: tuple[NonEmpty, ...]
    baseline_total: Decimal = Field(ge=0, allow_inf_nan=False)
    functional_unit: NonEmpty
    currency: NonEmpty

    @model_validator(mode="after")
    def complete_mapping(self) -> Self:
        """Require one accounting disposition per resource, with no double counts."""
        baseline = {x.resource_id: x for x in self.baseline}
        candidate = {x.resource_id: x for x in self.candidate}
        if not baseline or len(baseline) != len(self.baseline):
            msg = "Baseline resources are empty or duplicated"
            raise ValueError(msg)
        if len(candidate) != len(self.candidate):
            msg = "Candidate resources are duplicated"
            raise ValueError(msg)
        if any(x.currency != self.currency for x in (*self.baseline, *self.candidate)):
            msg = "Resource currency differs from comparison currency"
            raise ValueError(msg)
        dispositions = {x.baseline_resource_id: x for x in self.dispositions}
        if (
            len(dispositions) != len(self.dispositions)
            or dispositions.keys() != baseline.keys()
        ):
            msg = "Baseline resource disposition coverage differs"
            raise ValueError(msg)
        mapped = [
            resource_id
            for d in self.dispositions
            for resource_id in (*d.candidate_resource_ids, *d.stranded_resource_ids)
        ]
        all_candidate_ids = (*mapped, *self.added_candidate_ids)
        if len(set(all_candidate_ids)) != len(all_candidate_ids):
            msg = "Candidate resource counted more than once"
            raise ValueError(msg)
        if set(all_candidate_ids) != candidate.keys():
            msg = "Candidate resource coverage differs"
            raise ValueError(msg)
        self._check_retained(baseline, candidate)
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.traps[Inexact] = True
            if (
                sum((x.cost() for x in self.baseline), Decimal(0))
                != self.baseline_total
            ):
                msg = "Resource lines do not replay the declared baseline"
                raise ValueError(msg)
        return self

    def _check_retained(
        self,
        baseline: dict[str, ResourceLine],
        candidate: dict[str, ResourceLine],
    ) -> None:
        for disposition in self.dispositions:
            if disposition.action == "retained":
                if disposition.candidate_resource_ids != (
                    disposition.baseline_resource_id,
                ):
                    msg = "Retained resource must preserve its identity"
                    raise ValueError(msg)
                if (
                    candidate[disposition.baseline_resource_id]
                    != baseline[disposition.baseline_resource_id]
                ):
                    msg = "Retained resource must preserve its baseline line"
                    raise ValueError(
                        msg,
                    )

    def calculate_draft(self) -> tuple[Decimal, Decimal]:
        """Return candidate total and delta; no evidence qualification is implied."""
        checked = DraftResourceComparison.model_validate(self.model_dump())
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.traps[Inexact] = True
            total = sum((x.cost() for x in checked.candidate), Decimal(0))
            return total, total - checked.baseline_total


class ResourceParameterBinding(BaseModel):
    """Name the parameter identities underlying one declared resource line."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    arm: Literal["baseline", "candidate"]
    resource_id: NonEmpty
    quantity_parameter_id: NonEmpty
    unit_cost_parameter_id: NonEmpty
    allocation_parameter_id: NonEmpty


class DraftParameterBindings(BaseModel):
    """Bind draft arithmetic to exact parameter values, not source qualification."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter_version_id: NonEmpty
    baseline_total_parameter_id: NonEmpty
    lines: tuple[ResourceParameterBinding, ...]

    def verify_values(
        self,
        draft: DraftResourceComparison,
        parameters: ParameterSet,
    ) -> None:
        """Verify parameter values and exact unit labels; source checks are separate."""
        checked = DraftParameterBindings.model_validate(self.model_dump())
        draft = DraftResourceComparison.model_validate(draft.model_dump())
        parameters = ParameterSet.model_validate(parameters.model_dump())
        if parameters.version_id != checked.parameter_version_id:
            msg = "Resource parameter version differs"
            raise ValueError(msg)
        lines = {
            (arm, line.resource_id): line
            for arm, values in (
                ("baseline", draft.baseline),
                ("candidate", draft.candidate),
            )
            for line in values
        }
        bindings = {(x.arm, x.resource_id): x for x in checked.lines}
        if len(bindings) != len(checked.lines) or bindings.keys() != lines.keys():
            msg = "Resource parameter binding coverage differs"
            raise ValueError(msg)
        values = {p.parameter_id: p for p in parameters.parameters}
        _verify_bound_value(
            values,
            checked.baseline_total_parameter_id,
            draft.baseline_total,
            f"{draft.currency}/{draft.functional_unit}",
        )
        for key, binding in bindings.items():
            line = lines[key]
            _verify_bound_value(
                values,
                binding.quantity_parameter_id,
                line.quantity,
                f"{line.quantity_unit}/{draft.functional_unit}",
            )
            _verify_bound_value(
                values,
                binding.unit_cost_parameter_id,
                line.unit_cost,
                f"{line.currency}/{line.cost_denominator_unit}",
            )
            _verify_bound_value(
                values,
                binding.allocation_parameter_id,
                line.allocation,
                "fraction",
            )


def _verify_bound_value(
    parameters: dict[str, Parameter],
    parameter_id: str,
    expected: Decimal,
    unit: str,
) -> None:
    parameter = parameters.get(parameter_id)
    if (
        parameter is None
        or parameter.status == "unresolved"
        or parameter.derived_value is None
    ):
        msg = "Resource parameter missing or unresolved"
        raise ValueError(msg)
    try:
        value = Decimal(parameter.derived_value)
    except InvalidOperation as exc:
        msg = "Resource parameter value is not numeric"
        raise ValueError(msg) from exc
    if not value.is_finite() or value != expected or parameter.unit != unit:
        msg = "Resource parameter value or unit differs"
        raise ValueError(msg)
