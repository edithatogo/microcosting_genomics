# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check the inputs used by equipment, consumable and labour cost tables."""

from pathlib import Path

from scripts.parse_cost_tables import (
    parse_consumable_costs,
    parse_equipment_costs,
    parse_labour_costs,
)
from tests.checks import require_equal

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_parse_equipment_costs() -> None:
    """Check parse equipment costs."""
    minimum_equipment_rows = 50
    df = parse_equipment_costs(DATA_DIR / "Eq - Costs and Usage - VCGS.csv")
    if not (df.shape[0] > minimum_equipment_rows):
        raise AssertionError
    require_equal(df.shape[1], 33)
    if not (df.columns[0].startswith("Equipment")):
        raise AssertionError


def test_parse_consumable_costs() -> None:
    """Check parse consumable costs."""
    minimum_consumable_rows = 100
    df = parse_consumable_costs(DATA_DIR / "Cons -  Costs and Util - VCGS.csv")
    if not (df.shape[0] > minimum_consumable_rows):
        raise AssertionError
    require_equal(df.shape[1], 17)
    if not (df.columns[0] == "Stage"):
        raise AssertionError


def test_parse_labour_costs() -> None:
    """Check parse labour costs."""
    minimum_labour_rows = 20
    df = parse_labour_costs(DATA_DIR / "Labour - Costs - VCGS.csv")
    if not (df.shape[0] > minimum_labour_rows):
        raise AssertionError
    require_equal(df.shape[1], 30)
    if not (df.columns[0].startswith("Jurisdiction")):
        raise AssertionError
