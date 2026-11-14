# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify explicit joint scenarios without deriving probabilities from ranges."""

import json
from decimal import Decimal
from fractions import Fraction
lazy from pathlib import Path

import pytest

from genomics_microcosting.batch_uncertainty import simulate_batch_uncertainty
from tests import checks
from tests.test_dynamic_batch import dynamic, timed
from tests.test_static_batch_cost import batch_inputs


def recipe(tmp_path: Path) -> Path:
    """Retain a synthetic two-state joint distribution with explicit weights."""
    path = tmp_path / "ensemble.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "joint-batch-ensemble-v1",
                "assumption_basis": "synthetic joint probabilities",
                "evidence_state": "assumed",
                "states": [
                    {
                        "scenario_id": "early-fast",
                        "weight": 1,
                        "arrivals": [
                            {"case_id": "c0", "seconds": "0"},
                            {"case_id": "c1", "seconds": "0"},
                        ],
                        "run_duration_seconds": "2",
                        "windows": [{"start_seconds": "0", "end_seconds": "10"}],
                    },
                    {
                        "scenario_id": "spread-slow",
                        "weight": 3,
                        "arrivals": [
                            {"case_id": "c0", "seconds": "0"},
                            {"case_id": "c1", "seconds": "4"},
                        ],
                        "run_duration_seconds": "3",
                        "windows": [{"start_seconds": "0", "end_seconds": "10"}],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    return path


def test_joint_sampling_preserves_pairs_and_exact_weighted_cost(tmp_path: Path) -> None:
    """Do not independently recombine arrival and duration from different states."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    args = (path, timed(2), dynamic(), pricing, context)
    first = simulate_batch_uncertainty(*args, seed=7, draws=8)
    repeated = simulate_batch_uncertainty(*args, seed=7, draws=8)
    checks.require_equal(first, repeated)
    checks.require_equal(first.draw_indices, (1, 1, 1, 1, 1, 1, 1, 0))
    checks.require_equal(first.feasible_probability, Fraction(1))
    checks.require_equal(first.mean_complete_service_cost, Fraction(469, 8))
    checks.require_equal(
        tuple(o.result.cost.total_cost for o in first.outcomes),
        (Decimal("39.5"), Decimal(65)),
    )
    checks.require_equal(
        first.outcomes[1].turnarounds,
        (("c0", Decimal(4)), ("c1", Decimal(4))),
    )
    changed = simulate_batch_uncertainty(*args, seed=8, draws=8)
    checks.require_equal(int(first.input_sha256 == changed.input_sha256), 0)


def test_partial_service_does_not_produce_complete_service_mean(tmp_path: Path) -> None:
    """An infeasible state keeps unserved demand and its declared probability."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    data = json.loads(path.read_text())
    data["states"][1]["windows"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=8,
    )
    checks.require_equal(result.feasible_probability, Fraction(1, 4))
    checks.require_equal(result.mean_complete_service_cost, None)
    checks.require_equal(
        result.outcomes[1].result.schedule.unserved_case_ids,
        ("c0", "c1"),
    )


def test_scenario_scope_and_sampling_bounds_are_checked(tmp_path: Path) -> None:
    """Reject incomplete case coverage, duplicate states and invalid sample sizes."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    for seed, draws in ((True, 2), (-1, 2), (1, 0), (1, 10001)):
        with pytest.raises(ValueError, match="sampling"):
            simulate_batch_uncertainty(
                path,
                timed(2),
                dynamic(),
                pricing,
                context,
                seed=seed,
                draws=draws,
            )
    original = path.read_text()
    for change in ("case", "duplicate", "weight", "empirical"):
        data = json.loads(original)
        if change == "case":
            data["states"][1]["arrivals"][0]["case_id"] = "unknown"
        elif change == "duplicate":
            data["states"][1]["scenario_id"] = data["states"][0]["scenario_id"]
        elif change == "weight":
            data["states"][0]["weight"] = 0
        else:
            data["evidence_state"] = "measured"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(
            ValueError,
            match=r"coverage|Duplicate|weight|evidence_state",
        ):
            simulate_batch_uncertainty(
                path,
                timed(2),
                dynamic(),
                pricing,
                context,
                seed=1,
                draws=2,
            )


def test_recipe_rejects_duplicate_keys_and_preserves_decimal_tokens(
    tmp_path: Path,
) -> None:
    """Ambiguous keys and float conversion must not change probability or timing."""
    pricing, context = batch_inputs(tmp_path, "requested_tests")
    path = recipe(tmp_path)
    original = path.read_text()
    path.write_text(
        original.replace('"weight": 1', '"weight": 4, "weight": 1'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate JSON"):
        simulate_batch_uncertainty(
            path,
            timed(2),
            dynamic(),
            pricing,
            context,
            seed=7,
            draws=8,
        )
    path.write_text(
        original.replace(
            '"run_duration_seconds": "2"',
            '"run_duration_seconds": 2.12345678901234567890123456789',
        ),
        encoding="utf-8",
    )
    result = simulate_batch_uncertainty(
        path,
        timed(2),
        dynamic(),
        pricing,
        context,
        seed=7,
        draws=8,
    )
    checks.require_equal(
        result.outcomes[0].turnarounds[0][1],
        Decimal("3.12345678901234567890123456789"),
    )
