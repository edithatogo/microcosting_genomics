from pathlib import Path

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
from unimelb_phd_phase_1.config import load_config


def get_workbook_path() -> Path:
    cfg = load_config()
    key = cfg.get("default_workbook", "main")
    path = Path(cfg["workbooks"][key]["path"])
    if not path.exists():
        alt = cfg.get("workbooks", {}).get("validation", {}).get("path")
        if alt and Path(alt).exists():
            path = Path(alt)
    return path


def test_parse_dsa_equipment_throughput():
    df = parse_dsa_equipment_throughput(get_workbook_path())
    assert df.shape == (77, 34)
    assert df.columns[0].startswith("Panel - Estimate")


def test_parse_dsa_overheads():
    df = parse_dsa_overheads(get_workbook_path())
    assert df.shape == (77, 31)
    assert df.columns[0].startswith("Panel - Estimate")


def test_parse_dsa_consumable_discounts():
    df = parse_dsa_consumable_discounts(get_workbook_path())
    assert df.shape == (77, 34)
    assert df.columns[1].startswith("Equipment")


def test_parse_dsa_labour_prices():
    df = parse_dsa_labour_prices(get_workbook_path())
    assert df.shape == (77, 52)
    assert df.columns[1].startswith("Equipment")


def test_parse_summary_table():
    df = parse_summary_table(get_workbook_path())
    assert df.shape == (77, 16)
    assert df.columns[0].startswith("Panel")


def test_parse_process_table():
    df = parse_process_table(get_workbook_path())
    assert df.shape[1] == 2
    assert list(df.columns) == ["Stage", "Step"]


def test_parse_at_a_glance():
    df = parse_at_a_glance(get_workbook_path())
    assert df.shape[1] == 9
    assert list(df.columns[:3]) == ["Stage", "Sub-Stage", "Component"]


def test_parse_psa_table():
    csv_path = Path(
        "data/Microcosting - Study 1 - Utilisation and Microcosts v14 (20230814) PSA.csv"
    )
    df = parse_psa_table(csv_path)
    assert df.shape[0] > 0
    assert list(df.columns[:4]) == ["Test", "Category", "Stage", "LL"]
