# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Disposition handoffs cover the exact catalogue without enabling costs."""

import json
from hashlib import sha256
from typing import Any
lazy from pathlib import Path

import pytest

from genomics_microcosting.candidate_dispositions import (
    read_disposition_manifests,
    read_dispositions,
)
from tests.checks import require_equal


@pytest.fixture
def packet(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Build an independently declared synthetic catalogue and handoff."""
    catalogue = {
        "format_version": "1.0.0",
        "workbook_sha256": "a" * 64,
        "process_source_rows_sha256": "b" * 64,
        "sources": [
            {
                "source_id": "s",
                "title": "Synthetic source",
                "url": "https://example.org",
                "locator": "page 1",
                "edition": "v1",
                "accessed": "2026-11-07",
                "evidence_class": "primary_study",
                "source_snapshot_sha256": "c" * 64,
                "limitation": "Synthetic; no local applicability",
            },
        ],
        "candidates": [
            {
                "candidate_id": "c",
                "label": "Synthetic candidate",
                "source_ids": ["s"],
                "baseline_locations": ["WB18:A12"],
                "process_relationship": "unknown",
                "evidence_state": "research_lead",
                "unknowns": ["local scope"],
            },
        ],
        "scenarios": [
            {
                "scenario_id": "s1",
                "candidate_id": "c",
                "kind": "conditional_substitution",
                "baseline_identity": "a" * 64,
                "limitations": ["Synthetic"],
            },
        ],
    }
    catalogue_path = tmp_path / "catalogue.json"
    catalogue_path.write_text(json.dumps(catalogue), encoding="utf-8")
    data = {
        "format_version": "1.0.0",
        "assessment_date": "2026-11-07",
        "catalogue_sha256": sha256(catalogue_path.read_bytes()).hexdigest(),
        "workbook_sha256": "a" * 64,
        "scope": "Synthetic",
        "original_obligations": "Semantic inventory open",
        "candidates": [
            {
                "candidate_id": "c",
                "scenario_id": "s1",
                "label": "Synthetic candidate",
                "disposition": "blocked",
                "interface_state": "Draft",
                "affected_output": "Cost delta",
                "baseline_anchors": ["WB18:A12"],
                "source_records": [
                    {
                        "source_id": "s",
                        "locator": "page 1",
                        "edition": "v1",
                        "snapshot_sha256": "c" * 64,
                    },
                ],
                "candidate_blockers": ["Local scope unknown"],
                "required_input_manifest": None,
                "additional_scope_gap": "Complete manifest absent",
                "costing_available": False,
            },
        ],
    }
    return catalogue_path, tmp_path / "dispositions.json", data


def test_valid_packet_is_non_costing(
    packet: tuple[Path, Path, dict[str, Any]],
) -> None:
    """A matched blocked packet retains its explicitly unknown scope."""
    catalogue, path, data = packet
    path.write_text(json.dumps(data), encoding="utf-8")
    result = read_dispositions(path, catalogue)
    require_equal(result.candidates[0].costing_available, expected=False)
    require_equal(result.candidates[0].required_input_manifest, None)


@pytest.mark.parametrize(
    ("keys", "value", "error"),
    [
        (("workbook_sha256",), "d" * 64, "identity mismatch"),
        (("candidates",), [], "at least 1 item"),
        (("candidates", 0, "scenario_id"), "unknown", "scenario"),
        (("candidates", 0, "candidate_id"), "unknown", "exactly once"),
        (
            ("candidates", 0, "baseline_anchors"),
            ["WB18:A12", "WB18:A12"],
            "Duplicate disposition baseline",
        ),
        (("candidates", 0, "label"), "Different", "candidate"),
        (("candidates", 0, "baseline_anchors"), ["WB18:A13"], "anchors"),
        (
            ("candidates", 0, "source_records", 0, "source_id"),
            "unknown",
            "sources",
        ),
        (("candidates", 0, "source_records", 0, "edition"), "other", "context"),
        (("candidates", 0, "source_records", 0, "locator"), "other", "context"),
        (
            ("candidates", 0, "source_records", 0, "snapshot_sha256"),
            "d" * 64,
            "context",
        ),
        (("candidates", 0, "costing_available"), True, "False"),
        (("candidates", 0, "disposition"), "qualified", "blocked.*rejected"),
        (("candidates", 0, "candidate_blockers"), [], "at least 1 item"),
        (("candidates", 0, "additional_scope_gap"), None, "explicit scope gap"),
        (
            ("candidates", 0, "required_input_manifest"),
            {
                "version_id": "v1",
                "sha256": "d" * 64,
                "required_count": 1,
                "blocked_count": 2,
            },
            "Blocked count",
        ),
    ],
)
def test_packet_rejects_drift(
    packet: tuple[Path, Path, dict[str, Any]],
    keys: tuple[str | int, ...],
    value: object,
    error: str,
) -> None:
    """Reject missing scope, stale support and qualification claims."""
    catalogue, path, data = packet
    node: Any = data
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        read_dispositions(path, catalogue)


def test_catalogue_byte_change_is_rejected(
    packet: tuple[Path, Path, dict[str, Any]],
) -> None:
    """Even semantically neutral catalogue drift requires a new assessment."""
    catalogue, path, data = packet
    path.write_text(json.dumps(data), encoding="utf-8")
    catalogue.write_bytes(catalogue.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="identity mismatch"):
        read_dispositions(path, catalogue)


@pytest.mark.parametrize("collection", ["candidates", "source_records"])
def test_duplicate_coverage_is_rejected(
    packet: tuple[Path, Path, dict[str, Any]],
    collection: str,
) -> None:
    """Repeated candidates or references cannot masquerade as coverage."""
    catalogue, path, data = packet
    items = (
        data["candidates"]
        if collection == "candidates"
        else data["candidates"][0]["source_records"]
    )
    items.append(items[0])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"exactly once|Duplicate disposition"):
        read_dispositions(path, catalogue)


@pytest.fixture
def manifest_packet(
    packet: tuple[Path, Path, dict[str, Any]],
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, Any], Path, dict[str, Any]]:
    """Declare a blocked manifest with independent identity/counts."""
    catalogue, path, data = packet
    payload = {
        "version_id": "inputs-v1",
        "candidate_id": "c",
        "workbook_sha256": "a" * 64,
        "scope": "Declared synthetic scope",
        "required_ids": ["quantity"],
        "inputs": [
            {
                "input_id": "quantity",
                "resource_id": "kit",
                "role": "quantity",
                "parameter": None,
                "qualification": None,
                "blockers": ["No observed quantity"],
            },
        ],
    }
    manifest_path = tmp_path / "inputs.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    data["candidates"][0]["required_input_manifest"] = {
        "version_id": "inputs-v1",
        "sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "required_count": 1,
        "blocked_count": 1,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return catalogue, path, data, manifest_path, payload


def test_declared_manifest_bytes_are_checked(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
) -> None:
    """Actual blocked records are read without removing evidence blockers."""
    catalogue, path, _, manifest, _ = manifest_packet
    result = read_disposition_manifests(path, catalogue, {"c": manifest})
    require_equal(result[0].candidate_id, "c")
    require_equal(result[0].blocked_input_ids(), ("quantity",))
    with pytest.raises(ValueError, match="1 blocked requirements"):
        result[0].require_ready()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("candidate_id", "another"),
        ("version_id", "another"),
        ("workbook_sha256", "d" * 64),
        ("required_ids", ["quantity", "missing"]),
    ],
)
def test_manifest_context_and_coverage_are_checked(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
    key: str,
    value: object,
) -> None:
    """Even matching bytes cannot hide wrong context or missing records."""
    catalogue, path, data, manifest, payload = manifest_packet
    payload[key] = value
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    data["candidates"][0]["required_input_manifest"]["sha256"] = sha256(
        manifest.read_bytes(),
    ).hexdigest()
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"context or counts|coverage differs"):
        read_disposition_manifests(path, catalogue, {"c": manifest})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("required_count", 2),
        ("blocked_count", 0),
    ],
)
def test_manifest_counts_are_recomputed(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
    key: str,
    value: int,
) -> None:
    """Recompute required and blocked counts from the actual records."""
    catalogue, path, data, manifest, _ = manifest_packet
    data["candidates"][0]["required_input_manifest"][key] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="context or counts"):
        read_disposition_manifests(path, catalogue, {"c": manifest})


def test_manifest_byte_drift_is_rejected(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
) -> None:
    """Even whitespace drift requires a successor declaration."""
    catalogue, path, _, manifest, _ = manifest_packet
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="byte identity"):
        read_disposition_manifests(path, catalogue, {"c": manifest})


@pytest.mark.parametrize("keys", [(), ("other",), ("c", "other")])
def test_exact_manifest_mapping_is_required(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
    keys: tuple[str, ...],
) -> None:
    """Omissions and unsolicited files fail before opening any path."""
    catalogue, path, _, manifest, _ = manifest_packet
    with pytest.raises(ValueError, match="match exactly"):
        read_disposition_manifests(
            path,
            catalogue,
            dict.fromkeys(keys, manifest.with_name("absent.json")),
        )


def test_absent_manifest_remains_outside_scope(
    packet: tuple[Path, Path, dict[str, Any]],
) -> None:
    """An explicit scope gap does not become an empty ready manifest."""
    catalogue, path, data = packet
    path.write_text(json.dumps(data), encoding="utf-8")
    require_equal(read_disposition_manifests(path, catalogue, {}), ())
    require_equal(
        read_dispositions(path, catalogue).candidates[0].additional_scope_gap,
        "Complete manifest absent",
    )


def test_missing_declared_file_is_rejected(
    manifest_packet: tuple[Path, Path, dict[str, Any], Path, dict[str, Any]],
) -> None:
    """A declared manifest must actually exist at the selected path."""
    catalogue, path, _, manifest, _ = manifest_packet
    with pytest.raises(FileNotFoundError):
        read_disposition_manifests(
            path,
            catalogue,
            {"c": manifest.with_name("absent.json")},
        )
