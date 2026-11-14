# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Qualify writer option coverage and nondefault native output behavior."""

import inspect
import json
from datetime import date
lazy from collections.abc import Callable
lazy from pathlib import Path

import polars as pl
import pytest

from genomics_microcosting.loader_options import CSVOptions, ParquetOptions
from genomics_microcosting.loaders import (
    CSVLoader,
    JSONLoader,
    MetadataLoader,
    MultiFormatLoader,
    ParquetLoader,
)


@pytest.mark.parametrize(
    ("writer", "options"),
    [
        (pl.DataFrame.write_parquet, ParquetOptions),
        (pl.DataFrame.write_csv, CSVOptions),
    ],
)
def test_writer_contract_covers_locked_native_keywords(
    writer: Callable[..., object],
    options: type,
) -> None:
    """Detect new or removed writer keywords when the locked dependency changes."""
    expected = set(inspect.signature(writer).parameters) - {"self", "file"}
    if set(options.__annotations__) != expected:
        raise AssertionError


def test_nondefault_writer_options_preserve_identifiers_and_nulls(
    tmp_path: Path,
) -> None:
    """Round-trip real format controls without coercing a leading-zero identifier."""
    frame = pl.DataFrame({"id": ["001", "β"], "price": [1.25, None]})
    parquet = tmp_path / "values.parquet"
    csv = tmp_path / "values.csv"
    document = tmp_path / "values.json"
    ParquetLoader("parquet", parquet, compression="snappy", row_group_size=1).load(
        frame,
    )
    CSVLoader(
        "csv",
        csv,
        separator=";",
        include_bom=True,
        null_value="MISSING",
        quote_style="always",
    ).load(frame)
    JSONLoader("json", document, ensure_ascii=False).load(frame)
    if not pl.read_parquet(parquet).equals(frame):
        raise AssertionError
    actual = pl.read_csv(
        csv,
        separator=";",
        null_values="MISSING",
        schema_overrides={"id": pl.String},
    )
    if not actual.equals(frame):
        raise AssertionError
    if json.loads(document.read_text()) != frame.to_dicts():
        raise AssertionError
    if "β" not in document.read_text():
        raise AssertionError


def test_multiformat_invalid_options_do_not_hide_other_format_results(
    tmp_path: Path,
) -> None:
    """Keep format failures visible while attempting other requested outputs once."""
    loader = MultiFormatLoader(
        "formats",
        tmp_path,
        formats=["parquet", "csv"],
        separator=";",
    )
    with pytest.raises(RuntimeError, match="parquet"):
        loader.load(pl.DataFrame({"id": ["001"]}))
    if not (tmp_path / "data.csv").is_file():
        raise AssertionError
    if (tmp_path / "data.parquet").exists():
        raise AssertionError


def test_custom_json_encoder_keywords_remain_supported(tmp_path: Path) -> None:
    """Keep custom encoder keyword forwarding at the existing JSON boundary."""

    class PrefixEncoder(json.JSONEncoder):
        """Render a non-JSON scalar using an explicit synthetic prefix."""

        def __init__(self, *, prefix: str, **_settings: object) -> None:
            """Retain the custom codec setting alongside standard JSON settings."""
            super().__init__()
            self.prefix = prefix

        def default(self, o: object) -> str:
            """Format otherwise unsupported scalars without changing the table."""
            return self.prefix + str(o)

    loader = MultiFormatLoader(
        "custom-json",
        tmp_path,
        formats=["json"],
        cls=PrefixEncoder,
        prefix="fixture:",
    )
    loader.load(pl.DataFrame({"day": [date(2026, 1, 1)]}))
    if json.loads((tmp_path / "data.json").read_text()) != [
        {"day": "fixture:2026-01-01"},
    ]:
        raise AssertionError


def test_legacy_metadata_settings_keep_live_validation(
    tmp_path: Path,
) -> None:
    """Retain legacy positional settings without freezing an in-flight mapping."""
    validation: dict[str, object] = {}
    positional_flag = True
    loader = MetadataLoader("metadata", tmp_path, positional_flag, validation)
    if loader.validation_results is not validation:
        raise AssertionError
    validation["passed"] = True
    loader.load(pl.DataFrame({"id": ["001"]}))
    document = json.loads((tmp_path / "metadata.json").read_text())
    if document["data_info"]["data"]["validation_results"] != {"passed": True}:
        raise AssertionError
    duplicate_flag = False
    with pytest.raises(TypeError):
        MetadataLoader("metadata", tmp_path, duplicate_flag, include_validation=True)
