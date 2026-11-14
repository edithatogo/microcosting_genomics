# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Reject XML entities in workbook cells before returning input values."""

from io import BytesIO
from zipfile import ZipFile

import pytest
from openpyxl import Workbook, load_workbook


def test_workbook_xml_entities_are_rejected() -> None:
    """A tiny entity fixture must fail without expanding worksheet content."""
    source = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    if worksheet is None:
        raise AssertionError
    worksheet["A1"] = "synthetic-marker"
    workbook.save(source)
    workbook.close()
    tampered = BytesIO()
    with ZipFile(source) as original, ZipFile(tampered, "w") as modified:
        for entry in original.infolist():
            payload = original.read(entry)
            if entry.filename == "xl/worksheets/sheet1.xml":
                payload = (
                    b'<!DOCTYPE worksheet [<!ENTITY testentity "synthetic-expanded">]>'
                    + payload.replace(b"synthetic-marker", b"&testentity;")
                )
            modified.writestr(entry, payload)
    tampered.seek(0)
    with pytest.raises(ValueError, match="Unable to read workbook") as caught:
        load_workbook(tampered, read_only=True, data_only=True)
    cause = caught.value.__cause__
    if (
        cause is None
        or type(cause).__name__ != "EntitiesForbidden"
        or type(cause).__module__ != "defusedxml.common"
    ):
        raise AssertionError(cause)
