# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Cloud bills preserve signed adjustments and unknown cost/allocation scope."""

import json
from fractions import Fraction
from hashlib import sha256
from typing import Any

import pytest

from genomics_microcosting.cloud_billing import (
    AMOUNT_SEMANTICS,
    BillAllocation,
    CloudBillContext,
    allocate_cloud_bill,
)
from tests import checks


def bill_inputs() -> tuple[bytes, CloudBillContext, BillAllocation]:
    """Provide synthetic signed additive rows, never an actual provider bill."""
    kinds = (
        ("usage", "100", "80"),
        ("discount", "-10", "-8"),
        ("commitment_purchase", "40", "0"),
        ("commitment_adjustment", "0", "20"),
        ("credit", "-5", "-5"),
        ("tax", "12.5", "10.5"),
        ("fee", "2", "2"),
        ("refund", "-2", "-2"),
    )
    header = {
        "format_version": "cloud-bill-json-v1",
        "provider": "synthetic",
        "billing_account_id": "test-account",
        "invoice_id": "invoice-1",
        "exporter_version": "synthetic-v1",
        "currency": "AUD",
        "billing_start": "2026-10-01T00:00:00Z",
        "billing_end": "2026-11-01T00:00:00Z",
        "amount_semantics": AMOUNT_SEMANTICS,
    }
    data = {
        **header,
        "invoice_billed_total": "140",
        "invoice_effective_total": "100",
        "lines": [
            {
                "line_id": str(i),
                "kind": kind,
                "region": "test-region",
                "service": "synthetic-service",
                "instance": None,
                "resource_id": None,
                "commitment_id": None,
                "charge_start": None,
                "charge_end": None,
                "billed_quantity": None,
                "billed_unit": None,
                "billed_amount": billed,
                "effective_amount": effective,
                "description": "Synthetic additive amount, not a published rate",
            }
            for i, (kind, billed, effective) in enumerate(kinds)
        ],
    }
    payload = json.dumps(data).encode()
    context = CloudBillContext.model_validate(
        {
            **header,
            "source_sha256": sha256(payload).hexdigest(),
            "baseline_sha256": "a" * 64,
            "parameter_set_id": "params-v1",
            "process_graph_sha256": "b" * 64,
        },
    )
    allocation = BillAllocation.model_validate(
        {
            "function_version": "cloud-allocation-v1",
            "workload_id": "target",
            "tax_basis": "inclusive",
            "lines": tuple(
                {
                    "line_id": str(i),
                    "shares": (
                        {"workload_id": "target", "share": "0.25"},
                        {"workload_id": "other", "share": "0.5"},
                    ),
                }
                for i in range(len(kinds))
            ),
        },
    )
    return payload, context, allocation


def changed_bill(
    payload: bytes,
    context: CloudBillContext,
    keys: tuple[str | int, ...],
    value: object,
) -> tuple[bytes, CloudBillContext]:
    """Modify a synthetic field while honestly rebinding its source hash."""
    data = json.loads(payload)
    node: Any = data
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    changed = json.dumps(data).encode()
    return changed, context.model_copy(
        update={"source_sha256": sha256(changed).hexdigest()},
    )


def test_signed_bill_and_exact_conservation() -> None:
    """Reconcile all charge categories using independently calculated totals."""
    payload, context, allocation = bill_inputs()
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.billed.modeled_total, Fraction(275, 2))
    checks.require_equal(result.effective.modeled_total, Fraction(195, 2))
    checks.require_equal(result.billed.target_cost, Fraction(275, 8))
    checks.require_equal(result.effective.target_cost, Fraction(195, 8))
    checks.require_equal(result.billed.bill_residual, Fraction(5, 2))
    checks.require_equal(result.effective.bill_residual, Fraction(5, 2))
    for basis in (result.billed, result.effective):
        if (
            basis.target_cost is None
            or basis.other_cost is None
            or basis.unallocated_cost is None
        ):
            pytest.fail("Synthetic complete bill unexpectedly lacks cost")
        checks.require_equal(
            basis.target_cost + basis.other_cost + basis.unallocated_cost,
            basis.selected_total,
        )
    checks.require_equal(
        allocate_cloud_bill(payload, context, allocation),
        result,
    )


def test_tax_selection_does_not_change_invoice_reconciliation() -> None:
    """Tax exclusion retains the full signed invoice residual."""
    payload, context, allocation = bill_inputs()
    allocation = allocation.model_copy(update={"tax_basis": "exclusive"})
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.billed.selected_total, Fraction(125))
    checks.require_equal(result.effective.selected_total, Fraction(87))
    checks.require_equal(result.billed.target_cost, Fraction(125, 4))
    checks.require_equal(result.billed.bill_residual, Fraction(5, 2))
    checks.require_equal(result.billed.tax_total, Fraction(25, 2))


def test_unknown_effective_amount_is_not_billed_or_zero() -> None:
    """Unknown selected effective cost and residual remain undefined."""
    payload, context, allocation = bill_inputs()
    payload, context = changed_bill(
        payload,
        context,
        ("lines", 0, "effective_amount"),
        None,
    )
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.effective.modeled_total, None)
    checks.require_equal(result.effective.target_cost, None)
    checks.require_equal(result.effective.bill_residual, None)
    checks.require_equal(result.billed.modeled_total, Fraction(275, 2))
    checks.require_equal(result.unknown_effective_line_ids, ("0",))


@pytest.mark.parametrize(
    ("keys", "value", "error"),
    [
        (("provider",), "different", "context"),
        (("lines", 0, "line_id"), "1", "Duplicate"),
        (("lines", 0, "billed_amount"), "NaN", "decimal"),
        (("lines", 0, "billed_amount"), "1e999999", "decimal"),
        (("lines", 0, "billed_amount"), "-1", "sign"),
        (("lines", 1, "billed_amount"), "1", "sign"),
        (("lines", 0, "billed_quantity"), "1", "quantity"),
        (("lines", 0, "charge_start"), "2026-10-01T00:00:00Z", "period"),
        (("billing_end",), "2026-09-01T00:00:00Z", "period"),
        (("billing_start",), "2026-10-01T00:00:00", "timezone"),
        (("lines", 0, "unexpected"), "ignored?", "Extra inputs"),
    ],
)
def test_invalid_bill_fails_closed(
    keys: tuple[str | int, ...],
    value: object,
    error: str,
) -> None:
    """Invalid amounts, identities and incomplete scope never produce costs."""
    payload, context, allocation = bill_inputs()
    payload, context = changed_bill(payload, context, keys, value)
    with pytest.raises(ValueError, match=error):
        allocate_cloud_bill(payload, context, allocation)


def test_source_hash_and_duplicate_json_are_rejected() -> None:
    """Rehashing cannot legitimize an ambiguous duplicate-key bill."""
    payload, context, allocation = bill_inputs()
    with pytest.raises(ValueError, match="hash"):
        allocate_cloud_bill(payload + b"\n", context, allocation)
    payload = payload.replace(
        b'"provider": "synthetic"',
        b'"provider": "synthetic", "provider": "synthetic"',
    )
    context = context.model_copy(
        update={"source_sha256": sha256(payload).hexdigest()},
    )
    with pytest.raises(ValueError, match=r"Duplicate.*JSON"):
        allocate_cloud_bill(payload, context, allocation)


@pytest.mark.parametrize("case", ["missing", "duplicate", "overlap", "forged"])
def test_invalid_allocation_is_revalidated(case: str) -> None:
    """Require complete allocation coverage and finite shares."""
    payload, context, allocation = bill_inputs()
    line = allocation.lines[0]
    if case == "missing":
        allocation = allocation.model_copy(
            update={"lines": allocation.lines[1:]},
        )
    elif case == "duplicate":
        allocation = allocation.model_copy(
            update={"lines": (*allocation.lines, line)},
        )
    else:
        share = line.shares[0].model_copy(
            update={"share": "0.75" if case == "overlap" else "NaN"},
        )
        line = line.model_copy(update={"shares": (share, line.shares[1])})
        allocation = allocation.model_copy(
            update={"lines": (line, *allocation.lines[1:])},
        )
    with pytest.raises(ValueError, match=r"coverage|share|decimal"):
        allocate_cloud_bill(payload, context, allocation)


def test_empty_and_wholly_unallocated_bills() -> None:
    """Empty bills and explicitly unallocated rows conserve signed costs."""
    payload, context, allocation = bill_inputs()
    allocation = allocation.model_copy(
        update={
            "lines": tuple(
                line.model_copy(update={"shares": ()}) for line in allocation.lines
            ),
        },
    )
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.billed.target_cost, Fraction(0))
    checks.require_equal(result.billed.other_cost, Fraction(0))
    checks.require_equal(result.billed.unallocated_cost, Fraction(275, 2))
    payload, context = changed_bill(payload, context, ("lines",), [])
    allocation = allocation.model_copy(update={"lines": ()})
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.billed.modeled_total, Fraction(0))
    checks.require_equal(result.billed.bill_residual, Fraction(140))


def test_unknown_excluded_tax_preserves_known_effective_cost() -> None:
    """Excluded unknown tax leaves separately scoped costs known."""
    payload, context, allocation = bill_inputs()
    payload, context = changed_bill(
        payload,
        context,
        ("lines", 5, "effective_amount"),
        None,
    )
    allocation = allocation.model_copy(update={"tax_basis": "exclusive"})
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.effective.modeled_total, None)
    checks.require_equal(result.effective.tax_total, None)
    checks.require_equal(result.effective.selected_total, Fraction(87))
    checks.require_equal(result.effective.target_cost, Fraction(87, 4))
    checks.require_equal(result.effective.bill_residual, None)


def test_unknown_unallocated_charge_does_not_invent_target_cost() -> None:
    """An explicit zero share excludes a row without asserting zero row cost."""
    payload, context, allocation = bill_inputs()
    payload, context = changed_bill(
        payload,
        context,
        ("lines", 0, "effective_amount"),
        None,
    )
    allocation = allocation.model_copy(
        update={
            "lines": (
                allocation.lines[0].model_copy(update={"shares": ()}),
                *allocation.lines[1:],
            ),
        },
    )
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.effective.modeled_total, None)
    checks.require_equal(result.effective.unallocated_cost, None)
    checks.require_equal(result.effective.target_cost, Fraction(35, 8))


def test_credit_only_invoice_can_have_negative_net_cost() -> None:
    """A refund/credit is not clamped away or treated as consumed compute."""
    payload, context, allocation = bill_inputs()
    data = json.loads(payload)
    data["lines"] = [data["lines"][4]]
    data["invoice_billed_total"] = "-5"
    data["invoice_effective_total"] = "-5"
    payload = json.dumps(data).encode()
    context = context.model_copy(
        update={"source_sha256": sha256(payload).hexdigest()},
    )
    allocation = allocation.model_copy(update={"lines": (allocation.lines[4],)})
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.billed.target_cost, Fraction(-5, 4))
    checks.require_equal(result.billed.bill_residual, Fraction(0))


def test_raw_billing_dimensions_and_prior_charge_period_are_retained() -> None:
    """Billing dates do not silently reslice a prior-period adjustment."""
    payload, context, allocation = bill_inputs()
    data = json.loads(payload)
    line = data["lines"][1]
    line.update(
        {
            "charge_start": "2026-08-01T00:00:00+00:00",
            "charge_end": "2026-09-01T00:00:00+00:00",
            "billed_quantity": "-2.5",
            "billed_unit": "provider-GiB-month",
            "region": None,
            "instance": "explicit-instance",
            "commitment_id": "commitment-1",
            "resource_id": "resource-1",
        },
    )
    payload = json.dumps(data).encode()
    context = context.model_copy(
        update={"source_sha256": sha256(payload).hexdigest()},
    )
    result = allocate_cloud_bill(payload, context, allocation)
    observed = result.lines[1]
    checks.require_equal(observed.region, None)
    checks.require_equal(observed.billed_quantity, "-2.5")
    checks.require_equal(observed.billed_unit, "provider-GiB-month")
    checks.require_equal(observed.instance, "explicit-instance")
    checks.require_equal(observed.commitment_id, "commitment-1")
    checks.require_equal(observed.resource_id, "resource-1")
    checks.require_equal(result.billed.modeled_total, Fraction(275, 2))


def test_missing_effective_invoice_total_has_unknown_residual() -> None:
    """Row effective totals are not evidence of an invoice effective total."""
    payload, context, allocation = bill_inputs()
    payload, context = changed_bill(
        payload,
        context,
        ("invoice_effective_total",),
        None,
    )
    result = allocate_cloud_bill(payload, context, allocation)
    checks.require_equal(result.effective.modeled_total, Fraction(195, 2))
    checks.require_equal(result.effective.bill_residual, None)


def test_repeated_workload_share_and_model_identity_changes() -> None:
    """Duplicate shares fail; model versions change input identity."""
    payload, context, allocation = bill_inputs()
    first = allocate_cloud_bill(payload, context, allocation)
    changed = allocate_cloud_bill(
        payload,
        context.model_copy(update={"parameter_set_id": "params-v2"}),
        allocation,
    )
    if first.input_sha256 == changed.input_sha256:
        pytest.fail("Parameter identity did not enter the allocation digest")
    line = allocation.lines[0]
    line = line.model_copy(update={"shares": (line.shares[0], line.shares[0])})
    allocation = allocation.model_copy(
        update={"lines": (line, *allocation.lines[1:])},
    )
    with pytest.raises(ValueError, match="repeat"):
        allocate_cloud_bill(payload, context, allocation)
