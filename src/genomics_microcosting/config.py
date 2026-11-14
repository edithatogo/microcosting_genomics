# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Load workbook configuration with validated, non-coercing field contracts."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import yaml
from pydantic import ConfigDict, TypeAdapter, with_config


@with_config(ConfigDict(extra="allow", strict=True))
class SheetConfig(TypedDict, total=False):
    """Declare worksheet layout without dropping extension metadata."""

    header_rows: int
    data_starts_at: int
    skip_rows: int
    string_columns: list[str]
    column_mapping: dict[str, str]
    type_validation: dict[str, object]


@with_config(ConfigDict(extra="allow", strict=True))
class WorkbookConfig(TypedDict, total=False):
    """Declare a workbook path and its named worksheet contracts."""

    path: str
    sheets: dict[str, SheetConfig]


@with_config(ConfigDict(extra="allow", strict=True))
class ProjectConfig(TypedDict, total=False):
    """Preserve optional project configuration and unknown extension fields."""

    default_workbook: str
    workbooks: dict[str, WorkbookConfig]
    type_specifications: dict[str, dict[str, object]]
    column_metadata: dict[str, dict[str, object]]
    cost_config: dict[str, object]
    validation_rules: dict[str, object]


CONFIG_ADAPTER = TypeAdapter(ProjectConfig)
SHEET_CONFIG_ADAPTER = TypeAdapter(dict[str, SheetConfig])


def load_config(config_path: str | Path | None = None) -> ProjectConfig:
    """Load the YAML configuration file.

    This function loads the configuration from a YAML file, with support for
    fallback paths for backward compatibility.

    Args:
        config_path (str | Path | None, optional): Path to the configuration file.
            If None, tries default locations. Defaults to None.

    Returns:
        dict: The loaded configuration data.

    Raises:
        FileNotFoundError: If the configuration file cannot be found.
        ValueError: If there is an error parsing the YAML file.

    """
    if config_path is None:
        # Preserve the checkout and working-directory overrides, then use
        # the packaged default when running from an installed distribution.
        config_path = Path(__file__).resolve().parents[2] / "config.yaml"
        if not config_path.exists() and Path("config.yaml").is_file():
            config_path = Path("config.yaml")
        if not config_path.exists():
            alt = Path(__file__).resolve().parents[1] / "config.yaml"
            if alt.exists():
                config_path = alt
        if not config_path.exists():
            packaged = Path(__file__).resolve().parent / "config.yaml"
            if packaged.is_file():
                config_path = packaged
    else:
        config_path = Path(config_path)

    try:
        with config_path.open(encoding="utf-8") as fh:
            config_data = yaml.safe_load(fh)
            return CONFIG_ADAPTER.validate_python(
                config_data if config_data is not None else {},
            )
    except FileNotFoundError as error:
        message = f"Configuration file not found at: {config_path}"
        raise FileNotFoundError(message) from error
    except yaml.YAMLError as e:
        message = f"Error parsing configuration file at {config_path}: {e}"
        raise ValueError(
            message,
        ) from e
