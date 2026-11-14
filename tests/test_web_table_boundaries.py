# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Exercise native table rendering and escaped missing-resource responses."""

import html
import re
from http import HTTPStatus
from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.parse import quote

import polars as pl
from openpyxl import load_workbook

from genomics_microcosting.web import create_app

if TYPE_CHECKING:
    from pathlib import Path


def test_native_table_routes(tmp_path: Path) -> None:
    """Both preview and JSON routes consume list-valued native column names."""
    pl.DataFrame({"id": ["001"], "cost": [1.0]}).write_parquet(
        tmp_path / "source.parquet",
    )
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    app.testing = True
    client = app.test_client()
    preview = client.get("/table/source")
    if preview.status_code != HTTPStatus.OK or "001" not in preview.text:
        raise AssertionError(preview.status_code)
    result = client.get("/api/table/source")
    if result.status_code != HTTPStatus.OK or result.json != {
        "columns": ["id", "cost"],
        "data": [{"id": "001", "cost": 1.0}],
    }:
        raise AssertionError(result.text)


def test_missing_table_names_are_escaped(tmp_path: Path) -> None:
    """Unknown user-supplied names cannot become executable response markup."""
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    client = app.test_client()
    payload = "<img src=x onerror=alert(1)>"
    for prefix in ("/table/", "/visualize/table/"):
        response = client.get(prefix + quote(payload, safe=""))
        if response.status_code != HTTPStatus.NOT_FOUND or payload in response.text:
            raise AssertionError(response.text)


def test_table_name_does_not_enter_inline_javascript(tmp_path: Path) -> None:
    """HTML-escaped quotes must not re-enter JavaScript string literals."""
    table_name = "source');alert(1);('"
    pl.DataFrame({"id": ["001"]}).write_parquet(tmp_path / f"{table_name}.parquet")
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    response = app.test_client().get("/table/" + quote(table_name, safe=""))
    if response.status_code != HTTPStatus.OK:
        raise AssertionError(response.status_code)
    handlers = re.findall(r'onclick="([^"]*)"', response.text)
    if not handlers or any(table_name in html.unescape(code) for code in handlers):
        raise AssertionError(handlers)


def test_excel_export_preserves_formula_like_text(tmp_path: Path) -> None:
    """An exported data value cannot become an executable Excel formula."""
    source = pl.DataFrame({"=header": ["=1+1", "001", None]})
    source.write_parquet(tmp_path / "source.parquet")
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    response = app.test_client().get("/api/export/source/excel")
    if response.status_code != HTTPStatus.OK:
        raise AssertionError(response.status_code)
    book = load_workbook(BytesIO(response.data), data_only=False)
    try:
        sheet = book.active
        if sheet is None:
            raise AssertionError
        if list(sheet.values) != [("=header",), ("=1+1",), ("001",), (None,)]:
            raise AssertionError(list(sheet.values))
        if sheet["A1"].data_type != "s" or sheet["A2"].data_type != "s":
            message = "Formula-like data was exported as a formula"
            raise AssertionError(message)
    finally:
        book.close()


def test_pdf_report_backend_smoke(tmp_path: Path) -> None:
    """Exercise the declared optional PDF backend on the selected Python runtime."""
    pl.DataFrame({"id": ["001"]}).write_parquet(tmp_path / "source.parquet")
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    response = app.test_client().get("/api/generate-report")
    if response.status_code != HTTPStatus.OK or response.mimetype != "application/pdf":
        raise AssertionError(response.text)
    if not response.data.startswith(b"%PDF-") or not response.data.rstrip().endswith(
        b"%%EOF",
    ):
        raise AssertionError(response.data[:20])


def test_visualization_errors_omit_internal_details(tmp_path: Path) -> None:
    """An unexpected rendering failure must not echo internal paths to clients."""
    pl.DataFrame({"cost": [1.0]}).write_parquet(tmp_path / "source.parquet")
    with patch(
        "genomics_microcosting.monitoring.setup_standard_monitoring",
        return_value=(None,) * 5,
    ):
        app = create_app(tmp_path)
    with patch(
        "genomics_microcosting.web.generate_visualization",
        side_effect=ValueError("internal render path"),
    ):
        response = app.test_client().get("/api/generate_viz/source")
    if response.status_code != HTTPStatus.BAD_REQUEST:
        raise AssertionError(response.status_code)
    if response.json != {"success": False, "error": "Invalid visualization request"}:
        raise AssertionError(response.json)
