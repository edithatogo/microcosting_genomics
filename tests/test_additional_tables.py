# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check native readers for additional workbook tables."""

from pathlib import Path

from genomics_microcosting.config import load_config
from scripts.parse_additional_tables import (
    parse_at_a_glance,
    parse_dsa_consumable_discounts,
    parse_dsa_equipment_throughput,
    parse_dsa_labour_prices,
    parse_dsa_overheads,
    parse_process_table,
    parse_psa_table,
    parse_summary_table,
)
from tests.checks import require_equal


def get_workbook_path() -> Path:
    """Resolve the configured source workbook used by the supplemental readers."""
    cfg = load_config()
    key = cfg.get("default_workbook", "main")
    workbook = cfg.get("workbooks", {}).get(key, {}).get("path")
    if workbook is None:
        msg = f"Missing path for workbook {key!r}"
        raise KeyError(msg)
    path = Path(workbook)
    if not path.exists():
        alt = cfg.get("workbooks", {}).get("validation", {}).get("path")
        if alt and Path(alt).exists():
            path = Path(alt)
    return path


def test_parse_dsa_equipment_throughput() -> None:
    """Check equipment throughput shape and the first estimate header."""
    df = parse_dsa_equipment_throughput(get_workbook_path())
    if not (df.shape == (77, 34)):
        raise AssertionError
    if not (df.columns[0].startswith("Panel - Estimate")):
        raise AssertionError


def test_parse_dsa_overheads() -> None:
    """Check the overhead table shape and the first estimate header."""
    df = parse_dsa_overheads(get_workbook_path())
    if not (df.shape == (77, 31)):
        raise AssertionError
    if not (df.columns[0].startswith("Panel - Estimate")):
        raise AssertionError


def test_parse_dsa_consumable_discounts() -> None:
    """Check the discount table shape and the equipment identifier column."""
    df = parse_dsa_consumable_discounts(get_workbook_path())
    if not (df.shape == (77, 34)):
        raise AssertionError
    if not (df.columns[1].startswith("Equipment")):
        raise AssertionError


def test_parse_dsa_labour_prices() -> None:
    """Check labour price shape and the equipment identifier column."""
    df = parse_dsa_labour_prices(get_workbook_path())
    if not (df.shape == (77, 52)):
        raise AssertionError
    if not (df.columns[1].startswith("Equipment")):
        raise AssertionError


def test_parse_summary_table() -> None:
    """Check that the cost summary retains its panel estimate columns."""
    df = parse_summary_table(get_workbook_path())
    if not (df.shape == (77, 16)):
        raise AssertionError
    if not (df.columns[0].startswith("Panel")):
        raise AssertionError


def test_parse_process_table() -> None:
    """Check the process table's stage and step columns."""
    df = parse_process_table(get_workbook_path())
    require_equal(df.shape[1], 2)
    if not (list(df.columns) == ["Stage", "Step"]):
        raise AssertionError


def test_parse_at_a_glance() -> None:
    """Check the overview's width and its first three identifiers."""
    df = parse_at_a_glance(get_workbook_path())
    require_equal(df.shape[1], 9)
    if not (list(df.columns[:3]) == ["Stage", "Sub-Stage", "Component"]):
        raise AssertionError


def test_parse_psa_table() -> None:
    """Read the PSA data with identifiers and limits in source order."""
    csv_path = Path(
        "data",
        "Microcosting - Study 1 - Utilisation and Microcosts v14 (20230814) PSA.csv",
    )
    df = parse_psa_table(csv_path)
    if not (df.shape[0] > 0):
        raise AssertionError
    if not (list(df.columns[:4]) == ["Test", "Category", "Stage", "LL"]):
        raise AssertionError
