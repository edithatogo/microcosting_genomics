from __future__ import annotations

from pathlib import Path
import yaml


def load_config(config_path: str | Path | None = None) -> dict:
    """Load the YAML configuration file."""
    if config_path is None:
        config_path = Path(__file__).resolve().parents[1] / "config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
