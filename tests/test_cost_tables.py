from pathlib import Path

from scripts.parse_cost_tables import (
    parse_consumable_costs,
    parse_equipment_costs,
    parse_labour_costs,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_parse_equipment_costs():
    df = parse_equipment_costs(DATA_DIR / "Eq - Costs and Usage - VCGS.csv")
    assert df.shape[0] > 50
    assert df.shape[1] == 33
    assert df.columns[0].startswith("Equipment")


def test_parse_consumable_costs():
    df = parse_consumable_costs(DATA_DIR / "Cons -  Costs and Util - VCGS.csv")
    assert df.shape[0] > 100
    assert df.shape[1] == 17
    assert df.columns[0] == "Stage"


def test_parse_labour_costs():
    df = parse_labour_costs(DATA_DIR / "Labour - Costs - VCGS.csv")
    assert df.shape[0] > 20
    assert df.shape[1] == 30
    assert df.columns[0].startswith("Jurisdiction")
