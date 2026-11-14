# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Build the explicitly selected 2023 T1 scenario from source-bound records."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from genomics_microcosting.t1_workbook_builder import build_workbook_copy

ROOT = Path(__file__).resolve().parent.parent
TRACK = ROOT / "conductor/tracks/process_resource_alternatives_20261106"
VERSIONS = (
    "t1-reception-2023-v1",
    "t1-reception-2023-v2",
    "t1-reception-per-sample-v3",
    "t1-host-overlap-v4",
    "t1-combined-sensitivity-v5",
    "t1-wes80-quantity-v6",
    "t1-wes80-coverage-v7",
    "t1-support-plan-wes80-v8",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--version", required=True, choices=VERSIONS)
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=TRACK,
        help="Directory containing the selected scenario's source manifests",
    )
    args = parser.parse_args()
    if not args.manifest_dir.is_dir():
        parser.error("Scenario manifests are missing. Supply --manifest-dir.")
    return args


def main() -> None:
    """Build a new scenario workbook; native recalculation is a separate step."""
    args = _parse_args()
    manifest_dir: Path = args.manifest_dir
    branch = json.loads((manifest_dir / "t1-branch-corrections-v2.json").read_text())
    sensitivity = json.loads(
        (manifest_dir / "option2-compute-sensitivity-v1.json").read_text(),
    )
    reception = json.loads(
        (manifest_dir / "t1-reception-2023-v1.json").read_text(),
    )
    digest = reception["source_workbook_sha256"]
    if (
        digest != branch["baseline_sha256"]
        or digest != sensitivity["source_workbook_sha256"]
    ):
        msg = "Scenario source identities do not agree"
        raise ValueError(msg)
    if args.version == "t1-combined-sensitivity-v5":
        verify_combined_manifest(digest, manifest_dir=manifest_dir)
    changes = [
        {
            "sheet": c["sheet"],
            "cell": c["cell"],
            "original": c["source_formula"],
            "replacement": c["proposed_formula"],
        }
        for hypothesis in branch["corrects"]
        for c in hypothesis["changes"]
    ]
    if args.version not in {
        "t1-reception-per-sample-v3",
        "t1-combined-sensitivity-v5",
        "t1-wes80-quantity-v6",
        "t1-wes80-coverage-v7",
        "t1-support-plan-wes80-v8",
    }:
        changes.extend(
            {
                "sheet": c["sheet"],
                "cell": c["cell"],
                "original": c["source_formula"],
                "replacement": c["proposed_formula"],
            }
            for c in reception["change"]
        )
    changes.extend(
        [
            {
                "sheet": "BI - Comp Use - VCGS",
                "cell": "U105",
                "original": None,
                "replacement": sensitivity["low"],
            },
            {
                "sheet": "BI - Comp Use - VCGS",
                "cell": "W105",
                "original": None,
                "replacement": sensitivity["high"],
            },
            *[
                {
                    "sheet": "Detailed Table",
                    "cell": target,
                    "original": None,
                    "replacement": f"='BI - Comp Use - VCGS'!{source}{factor}",
                }
                for target, source, factor in [
                    ("M1050", "U105", ""),
                    ("O1050", "W105", ""),
                    ("M1299", "U105", "*3"),
                    ("O1299", "W105", "*3"),
                ]
            ],
        ],
    )
    if args.version in {
        "t1-reception-2023-v2",
        "t1-reception-per-sample-v3",
        "t1-host-overlap-v4",
        "t1-combined-sensitivity-v5",
        "t1-wes80-quantity-v6",
        "t1-wes80-coverage-v7",
        "t1-support-plan-wes80-v8",
    }:
        propagation = json.loads(
            (manifest_dir / "t1-compute-bound-propagation-v2.json").read_text(),
        )
        if propagation["source_workbook_sha256"] != digest:
            msg = "Compute-bound correction source identity does not agree"
            raise ValueError(msg)
        changes.extend(
            {
                "sheet": c["sheet"],
                "cell": c["cell"],
                "original": c["source_formula"],
                "replacement": c["proposed_formula"],
            }
            for c in propagation["change"]
        )
    if args.version in {
        "t1-reception-per-sample-v3",
        "t1-combined-sensitivity-v5",
        "t1-wes80-quantity-v6",
        "t1-wes80-coverage-v7",
        "t1-support-plan-wes80-v8",
    }:
        per_sample = json.loads(
            (manifest_dir / "t1-reception-per-sample-v3.json").read_text(),
        )
        if per_sample["source_workbook_sha256"] != digest:
            msg = "Per-sample reception source identity does not agree"
            raise ValueError(msg)
        changes.extend(
            {
                "sheet": c["sheet"],
                "cell": c["cell"],
                "original": c["source_formula"],
                "replacement": c["proposed_formula"],
            }
            for c in per_sample["change"]
        )
    if args.version in {"t1-host-overlap-v4", "t1-combined-sensitivity-v5"}:
        apply_host_overlap(changes, digest, manifest_dir=manifest_dir)
    if args.version in {
        "t1-wes80-quantity-v6",
        "t1-wes80-coverage-v7",
        "t1-support-plan-wes80-v8",
    }:
        apply_coverage_scenario(
            changes,
            digest,
            args.version,
            manifest_dir=manifest_dir,
        )
    build_workbook_copy(
        args.source,
        args.destination,
        source_sha256=digest,
        changes=changes,
        selected_version=args.version,
    )


def apply_coverage_scenario(
    changes: list[dict[str, object]],
    digest: str,
    version: str,
    *,
    manifest_dir: Path | None = None,
) -> None:
    """Apply the requested coverage scenario and optional support diagnostic."""
    if version == "t1-support-plan-wes80-v8":
        apply_support_plan_combination(changes, digest, manifest_dir=manifest_dir)
    else:
        apply_wes80_quantities(changes, digest, version, manifest_dir=manifest_dir)


def apply_support_plan_combination(
    changes: list[dict[str, object]],
    digest: str,
    *,
    manifest_dir: Path | None = None,
) -> None:
    """Compose the source-bound coverage and support-plan diagnostics."""
    version = "t1-support-plan-wes80-v8"
    root = manifest_dir or TRACK
    manifest = json.loads((root / f"{version}.json").read_text())
    expected = {"t1-wes80-coverage-v7.json", "t1-support-plan-af26-v1.json"}
    constituents = manifest.get("constituent_sha256", {})
    if (
        manifest.get("version") != version
        or manifest.get("source_workbook_sha256") != digest
        or set(constituents) != expected
        or any(
            sha256((root / name).read_bytes()).hexdigest() != value
            for name, value in constituents.items()
        )
    ):
        msg = "Support-plan combination source identities do not agree"
        raise ValueError(msg)
    apply_wes80_quantities(changes, digest, "t1-wes80-coverage-v7", manifest_dir=root)
    support = json.loads((root / "t1-support-plan-af26-v1.json").read_text())
    if support["source_sha256"] != digest:
        msg = "Support-plan source workbook identity mismatch"
        raise ValueError(msg)
    changes.append(
        {
            "sheet": support["sheet"],
            "cell": support["cell"],
            "original": support["source_formula"],
            "replacement": support["proposed_formula"],
        },
    )


def apply_wes80_quantities(
    changes: list[dict[str, object]],
    digest: str,
    version: str,
    *,
    manifest_dir: Path | None = None,
) -> None:
    """Select recorded 80x source quantities in the exome trio sensitivity."""
    root = manifest_dir or TRACK
    path = root / f"{version}.json"
    manifest = json.loads(path.read_text())
    base = root / "t1-reception-per-sample-v3.json"
    if (
        manifest["version"] != version
        or manifest["source_workbook_sha256"] != digest
        or sha256(base.read_bytes()).hexdigest() != manifest["base_manifest_sha256"]
    ):
        msg = "WES 80x scenario source identities do not agree"
        raise ValueError(msg)
    if version == "t1-wes80-coverage-v7":
        inherited = manifest.get("inherited_manifest_sha256", {})
        expected = {
            "t1-branch-corrections-v2.json",
            "option2-compute-sensitivity-v1.json",
            "t1-compute-bound-propagation-v2.json",
        }
        if set(inherited) != expected or any(
            sha256((root / name).read_bytes()).hexdigest() != file_digest
            for name, file_digest in inherited.items()
        ):
            msg = "WES 80x inherited scenario identity mismatch"
            raise ValueError(msg)
    changes.extend(
        {
            "sheet": item["sheet"],
            "cell": item["cell"],
            "original": item["source_formula"],
            "replacement": item["proposed_formula"],
        }
        for item in manifest["change"]
    )


def verify_combined_manifest(digest: str, *, manifest_dir: Path | None = None) -> None:
    """Verify the exact source identities of the combined sensitivity."""
    root = manifest_dir or TRACK
    manifest = json.loads((root / "t1-combined-sensitivity-v5.json").read_text())
    expected = {
        "t1-branch-corrections-v2.json",
        "option2-compute-sensitivity-v1.json",
        "t1-compute-bound-propagation-v2.json",
        "t1-reception-per-sample-v3.json",
        "t1-host-overlap-v4.json",
    }
    if (
        manifest["source_workbook_sha256"] != digest
        or set(manifest["constituent_sha256"]) != expected
    ):
        msg = "Combined scenario source identities do not agree"
        raise ValueError(msg)
    for filename, file_digest in manifest["constituent_sha256"].items():
        if sha256((root / filename).read_bytes()).hexdigest() != file_digest:
            msg = f"Combined scenario constituent changed: {filename}"
            raise ValueError(msg)


def apply_host_overlap(
    changes: list[dict[str, object]],
    digest: str,
    *,
    manifest_dir: Path | None = None,
) -> None:
    """Apply a conditional two-job allocation sensitivity to existing edits."""
    root = manifest_dir or TRACK
    overlap = json.loads((root / "t1-host-overlap-v4.json").read_text())
    if overlap["source_workbook_sha256"] != digest:
        msg = "Host-overlap source identity does not agree"
        raise ValueError(msg)
    targets = {
        "U105": overlap["remaining"]["low"],
        "V105": "=SUM(V69:V104)-V76-V100",
        "W105": overlap["remaining"]["high"],
    }
    selected = [
        item
        for item in changes
        if item["sheet"] == "BI - Comp Use - VCGS" and item["cell"] in targets
    ]
    if {item["cell"] for item in selected} != set(targets):
        msg = "Host-overlap scenario targets are incomplete"
        raise ValueError(msg)
    for item in selected:
        cell = item["cell"]
        if not isinstance(cell, str):
            msg = "Invalid host-overlap target"
            raise TypeError(msg)
        item["replacement"] = targets[cell]


if __name__ == "__main__":
    main()
