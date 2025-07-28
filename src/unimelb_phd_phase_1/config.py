from __future__ import annotations

from pathlib import Path

import yaml


def load_config(config_path: str | Path | None = None) -> dict:
    """Load the YAML configuration file."""
    if config_path is None:
        # By default load ``config.yaml`` from the repository root and
        # fall back to ``src/config.yaml`` for legacy setups. ``parents[2]``
        # points at the project root when installed in editable mode.
        config_path = Path(__file__).resolve().parents[2] / "config.yaml"
        if not config_path.exists():
            alt = Path(__file__).resolve().parents[1] / "config.yaml"
            if alt.exists():
                config_path = alt
    else:
        config_path = Path(config_path)

    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config_data = yaml.safe_load(fh)
            return config_data if config_data is not None else {}
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(
            f"Error parsing configuration file at {config_path}: {e}"
        ) from e
