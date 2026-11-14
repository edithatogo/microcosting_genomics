# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check the provider boundary before any shared numerical implementation."""

import json
from hashlib import sha256
from typing import Any, cast
lazy from pathlib import Path

import pytest

from genomics_microcosting.dapane_adapter import (
    ExtractionBatch,
    historical_manual_extraction,
    manual_dna_extraction_request,
)
from genomics_microcosting.dapane_workbook import inspect_manual_extraction_workbook
from tests import checks


def canonical(value: object) -> str:
    """Match the published artifact canonicalization, independently of the loader."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def seal(artifact: dict[str, Any]) -> tuple[str, str]:
    """Sign only explicit synthetic input declarations."""
    artifact["release_sha256"] = sha256(
        canonical(artifact["release_snapshot"]).encode(),
    ).hexdigest()
    unsigned = {k: v for k, v in artifact.items() if k != "artifact_sha256"}
    digest = sha256(canonical(unsigned).encode()).hexdigest()
    artifact["artifact_sha256"] = digest
    return canonical(artifact), digest


def artifact() -> dict[str, Any]:
    """Build a small synthetic wage release, never a real employment rule."""
    source = {
        "source_id": "synthetic-source", "title": "Synthetic reference",
        "uri": "https://example.org/synthetic", "edition": "fixture-v1",
        "jurisdiction": "synthetic", "kind": "synthetic", "holding": "held",
        "authority": "primary", "applicability": "verified", "sha256": "1" * 64,
        "retrieved_at": "2026-11-15T00:00:00+00:00",
        "published_on": "2026-09-01", "effective_from": "2026-09-01",
        "effective_to": None, "verified_through": "2026-11-16",
        "nominal_expiry": None, "employers": ["synthetic"],
        "classifications": ["synthetic"], "supersedes": [], "reason": "",
    }
    provider_quote = {
        "quote_id": "hourly", "component": "base_salary", "unit": "hour",
        "amount": "36.00", "starts_on": "2026-09-01", "ends_on": "2026-11-16",
        "known_from": "2026-11-15", "source_id": source["source_id"],
        "source_sha256": source["sha256"], "citation": source["uri"],
        "status": "accepted",
    }
    snapshot = {
        "release_id": "synthetic-v1", "method_id": "direct_unit_quote_v1",
        "currency": "AUD", "as_known_on": "2026-11-15",
        "jurisdiction": "synthetic", "employer": "synthetic",
        "classification": "synthetic", "sources": {"schema_version": 1, "records": [source]},
        "quotes": [provider_quote],
    }
    quote = {
        "id": "minute", "kind": "resource_use", "target": "laboratory-scientist",
        "unit": "minute", "amount": "36.00", "per_quantity": "60",
        "currency": "AUD", "price_year": 2026, "basis": "financial_cost",
        "components": ["base_salary"], "valid_from": "2026-09-01",
        "valid_to": "2026-11-16", "known_from": "2026-11-15",
        "source": {
            "id": source["source_id"], "version": "synthetic-v1",
            "evidence": "synthetic", "access": "public", "validation": "unvalidated",
            "content_digest": "sha256:" + source["sha256"],
            "locator": source["uri"],
        },
    }
    return {
        "schema_version": "workforce-dapane-quotes/1",
        "provider": {
            "name": "microcosting-healthworkforce", "version": "0.0.1",
            "method_id": "direct_unit_quote_v1",
        },
        "release_id": "synthetic-v1", "as_known_on": "2026-11-15",
        "release_snapshot": snapshot,
        "bindings": [{
            "provider_quote_id": "hourly", "quote_id": "minute",
            "target": "laboratory-scientist", "unit": "minute",
            "per_quantity": "60", "components": ["base_salary"],
            "component_basis": "Synthetic base only; excludes all on-costs",
            "price_year": 2026,
        }],
        "quotes": [quote],
    }


def request(
    batches: tuple[ExtractionBatch, ...] | None = None,
    *,
    declaration: dict[str, Any] | None = None,
    **changes: object,
) -> dict[str, Any]:
    """Build an explicit synthetic invocation, leaving economics to Rust."""
    raw, digest = seal(artifact() if declaration is None else declaration)
    options: dict[str, Any] = {
        "release_digest": digest, "quote_id": "minute",
        "batches": (ExtractionBatch("batch", ("a", "b", "c")),) if batches is None else batches,
        "service_date": "2026-11-15", "knowledge_cutoff": "2026-11-15",
        "role_mapping_basis": "Synthetic role mapping; no classification equivalence",
        "run_id": "synthetic-manual-extraction",
    }
    options.update(changes)
    return manual_dna_extraction_request(raw, **options)


def test_shared_batch_retains_two_physical_resource_uses() -> None:
    """A partial batch retains the original shared effort without sample scaling."""
    result = request()
    checks.require_equal([u["quantity"] for u in result["usage"]], ["30", "5"])
    checks.require_equal(len(result["allocations"]), 1)
    checks.require_equal(
        result["allocations"][0]["weights"],
        [{"object_id": name, "weight": "1"} for name in ("a", "b", "c")],
    )
    checks.require_equal(result["quotes"][0]["components"], ["base_salary"])
    checks.require_equal(result["quotes"][0]["per_quantity"], "60")


def test_failed_then_repeated_batch_keeps_separate_pools() -> None:
    """A failed attempt does not erase incurred labour or merge its rounding pool."""
    result = request((
        ExtractionBatch("first", ("a", "b", "c"), outcome="failed"),
        ExtractionBatch("retry", ("a", "b", "c"), repeat_of="first"),
    ))
    checks.require_equal(len(result["usage"]), 4)
    checks.require_equal(len(result["allocations"]), 2)
    checks.require_equal(len({u["use_id"] for u in result["usage"]}), 4)


@pytest.mark.parametrize("members", [(), ("a",) * 2, tuple("abcdefg"), "abc"])
def test_invalid_cohorts_fail_before_pricing(members: object) -> None:
    """Missing, duplicated, excessive or ambiguous membership cannot be allocated."""
    with pytest.raises(ValueError, match="specimen"):
        request((ExtractionBatch("batch", cast("tuple[str, ...]", members)),))


@pytest.mark.parametrize(
    "batches",
    [
        (ExtractionBatch("a", ("x",)), ExtractionBatch("a", ("y",))),
        (ExtractionBatch("a", ("x",)), ExtractionBatch("b", ("x",))),
        (ExtractionBatch("a", ("x",), repeat_of="unknown"),),
        (ExtractionBatch("a", ("x",)), ExtractionBatch("b", ("x",), repeat_of="a")),
        (ExtractionBatch("a", ("x",), outcome="failed"), ExtractionBatch("b", ("y",), repeat_of="a")),
        (
            ExtractionBatch("a", ("x",), outcome="failed"),
            ExtractionBatch("b", ("x",), repeat_of="a"),
            ExtractionBatch("c", ("x",), repeat_of="a"),
        ),
    ],
)
def test_invalid_attempt_histories_fail_closed(batches: tuple[ExtractionBatch, ...]) -> None:
    """No independent alias, success retry, forward reference or fork is inferred."""
    with pytest.raises(ValueError, match="batch|repeat|specimen"):
        request(batches)


@pytest.mark.parametrize(
    "changes",
    [
        {"knowledge_cutoff": "2026-11-14"},
        {"service_date": "2026-11-16"},
        {"service_date": "2026-08-31"},
        {"role_mapping_basis": ""},
        {"quote_id": "unknown"},
        {"release_digest": "0" * 64},
    ],
)
def test_missing_date_scope_or_pinned_identity_fails(changes: dict[str, str]) -> None:
    """An accepted release does not imply arbitrary date or role applicability."""
    with pytest.raises(ValueError):
        request(**changes)


@pytest.mark.parametrize("mutation", ["amount", "components", "extra_component", "source_kind", "status", "release"])
def test_signed_but_inconsistent_projection_is_rejected(mutation: str) -> None:
    """A self-consistent hash cannot conceal broken release-to-quote lineage."""
    declaration = artifact()
    if mutation == "amount":
        declaration["quotes"][0]["amount"] = "37.00"
    elif mutation == "components":
        declaration["quotes"][0]["components"] = ["base_salary", "base_salary"]
    elif mutation == "extra_component":
        declaration["quotes"][0]["components"] = ["base_salary", "oncosts"]
        declaration["bindings"][0]["components"] = ["base_salary", "oncosts"]
    elif mutation == "source_kind":
        declaration["release_snapshot"]["sources"]["records"][0]["kind"] = "unknown"
    elif mutation == "status":
        declaration["release_snapshot"]["quotes"][0]["status"] = "candidate"
    else:
        declaration["release_snapshot"]["release_id"] = "different"
    with pytest.raises(ValueError):
        request(declaration=declaration)


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":1.2}', '{"x":NaN}', '{"x":Infinity}'])
def test_ambiguous_json_transport_is_rejected(raw: str) -> None:
    """Duplicate keys and binary/nonfinite tokens never become accepted artifacts."""
    with pytest.raises(ValueError):
        manual_dna_extraction_request(
            raw, release_digest="0" * 64, quote_id="minute",
            batches=(ExtractionBatch("batch", ("a",)),),
            service_date="2026-11-15", knowledge_cutoff="2026-11-15",
            role_mapping_basis="synthetic", run_id="synthetic",
        )


def test_old_entry_point_is_an_explicit_passthrough() -> None:
    """The rollback adapter retains old values, source coordinates and errors."""
    class Legacy:
        """Retain a deliberate missing legacy cell value."""

        def get_cell_value(self, sheet: str, cell: str) -> object:
            """Return the original fixture value without transformation."""
            checks.require_equal(sheet, "Labour - Usage - VCGS")
            return {"AB22": "lab", "AB23": None, "AB24": "subtotal"}[cell]
    checks.require_equal(
        historical_manual_extraction(Legacy()),
        {"AB22": "lab", "AB23": None, "AB24": "subtotal"},
    )


def test_unrecognized_workbook_bytes_cannot_claim_the_source(tmp_path: Path) -> None:
    """Do not label a synthetic or repaired file as the preserved workbook."""
    source = tmp_path / "synthetic.xlsm"
    source.write_bytes(b"synthetic non-workbook")
    with pytest.raises(ValueError, match="hash"):
        inspect_manual_extraction_workbook(source)


@pytest.mark.parametrize(("source", "projected"), [("1E+2", "100"), ("1E-7", "0.0000001")])
def test_exact_exponent_projection_is_transport_not_revaluation(
    source: str, projected: str,
) -> None:
    """A valid Decimal serialization keeps the same exactly represented amount."""
    declaration = artifact()
    declaration["release_snapshot"]["quotes"][0]["amount"] = source
    declaration["quotes"][0]["amount"] = projected
    checks.require_equal(
        request(declaration=declaration)["quotes"][0]["amount"],
        projected,
    )


@pytest.mark.parametrize("field", ["employers", "classifications"])
def test_scope_strings_cannot_pass_substring_membership(field: str) -> None:
    """The consumer preserves the provider's array semantics after a rehash."""
    declaration = artifact()
    declaration["release_snapshot"]["sources"]["records"][0][field] = "not-synthetic-authorized"
    with pytest.raises(ValueError, match="array"):
        request(declaration=declaration)


@pytest.mark.parametrize("amount", ["1E+97", "1E-37", "-0", "NaN", "Infinity"])
def test_unbounded_or_nonfinite_source_amounts_fail_closed(amount: str) -> None:
    """A signed artifact cannot waive the shared exact numeric contract."""
    declaration = artifact()
    declaration["release_snapshot"]["quotes"][0]["amount"] = amount
    with pytest.raises(ValueError, match="amount"):
        request(declaration=declaration)
