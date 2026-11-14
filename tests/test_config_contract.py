# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Preserve source configuration while rejecting invalid layout field types."""

lazy from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import genomics_microcosting.config as config_module
from genomics_microcosting.config import load_config


def test_configuration_preserves_extension_fields(tmp_path: Path) -> None:
    """Retain optional metadata at every level without coercing source values."""
    source = {
        "extra": {"retained": True},
        "workbooks": {
            "test": {
                "path": "original.xlsx",
                "release": "v1",
                "sheets": {"Sheet1": {"header_rows": 2, "source_note": "retained"}},
            },
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(source))
    before = path.read_bytes()
    if not (load_config(path) == source):
        raise AssertionError
    if not (path.read_bytes() == before):
        raise AssertionError


@pytest.mark.parametrize("invalid", ['"2"', "true", "[2]"])
def test_configuration_rejects_invalid_header_type(
    tmp_path: Path,
    invalid: str,
) -> None:
    """Do not silently coerce string, boolean or list header counts."""
    path = tmp_path / "config.yaml"
    path.write_text(
        "workbooks:\n  test:\n    sheets:\n      S:\n        header_rows: " + invalid,
    )
    with pytest.raises(ValidationError):
        load_config(path)


def test_empty_configuration_retains_legacy_empty_mapping(tmp_path: Path) -> None:
    """Do not manufacture default workbook definitions for an empty source."""
    path = tmp_path / "config.yaml"
    path.write_text("")
    if not (load_config(path) == {}):
        raise AssertionError


def test_installed_default_and_working_directory_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use packaged defaults only when no prior configuration exists."""
    package = tmp_path / "site" / "package"
    package.mkdir(parents=True)
    (package / "config.yaml").write_text("default_workbook: packaged\n")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(config_module, "__file__", str(package / "config.py"))
    monkeypatch.chdir(work)
    if load_config().get("default_workbook") != "packaged":
        raise AssertionError
    (work / "config.yaml").write_text("default_workbook: local\n")
    if load_config().get("default_workbook") != "local":
        raise AssertionError
    explicit = work / "explicit.yaml"
    explicit.write_text("default_workbook: explicit\n")
    if load_config(explicit).get("default_workbook") != "explicit":
        raise AssertionError
