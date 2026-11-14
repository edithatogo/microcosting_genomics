# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Build an explicitly selected, source-verified T1 workbook copy."""

import re
from hashlib import sha256
from html import escape
from typing import TYPE_CHECKING, Any
from zipfile import ZipFile
lazy from pathlib import Path

from defusedxml import ElementTree
from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from openpyxl.workbook import Workbook


def build_workbook_copy(
    source: Path,
    destination: Path,
    *,
    source_sha256: str,
    changes: Sequence[Mapping[str, Any]],
    selected_version: str,
) -> str:
    """Apply explicit cell changes to a new workbook after all preconditions pass.

    Returns the output file SHA-256. A workbook writer does not recalculate formulas.
    The caller must separately qualify calculation, rights, and scientific validity.
    """
    if not selected_version.strip():
        msg = "An explicit scenario version is required"
        raise ValueError(msg)
    if source.resolve() == destination.resolve() or destination.exists():
        msg = "Destination must be a new file distinct from the source"
        raise ValueError(msg)
    if sha256(source.read_bytes()).hexdigest() != source_sha256:
        msg = "Source workbook hash mismatch"
        raise ValueError(msg)
    if not changes:
        msg = "A scenario must specify changes"
        raise ValueError(msg)
    workbook = load_workbook(source, keep_vba=source.suffix.lower() == ".xlsm")
    try:
        seen: set[tuple[str, str]] = set()
        for item in changes:
            sheet, cell = item["sheet"], item["cell"]
            key = (sheet, cell)
            if key in seen:
                msg = "Duplicate workbook target"
                raise ValueError(msg)
            seen.add(key)
            column, row = coordinate_from_string(cell)
            if (
                workbook[sheet].cell(row, column_index_from_string(column)).value
                != item["original"]
            ):
                msg = f"Source precondition failed: {sheet}!{cell}"
                raise ValueError(msg)
        _write_overlay(source, destination, workbook, changes)
    finally:
        workbook.close()
    return sha256(destination.read_bytes()).hexdigest()


def _write_overlay(
    source: Path,
    destination: Path,
    workbook: Workbook,
    changes: Sequence[Mapping[str, Any]],
) -> None:
    """Patch only selected OOXML cells, expanding touched shared-formula groups."""
    with ZipFile(source) as original:
        catalog = ElementTree.fromstring(original.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(
            original.read("xl/_rels/workbook.xml.rels"),
        )
        targets = {
            element.attrib["Id"]: element.attrib["Target"] for element in relationships
        }
        rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        paths = {
            element.attrib["name"]: (
                targets[element.attrib[rid]].lstrip("/")
                if targets[element.attrib[rid]].startswith("/")
                else "xl/" + targets[element.attrib[rid]]
            )
            for element in catalog.findall(".//{*}sheet")
        }
        by_sheet: dict[str, list[Mapping[str, Any]]] = {}
        for change in changes:
            by_sheet.setdefault(change["sheet"], []).append(change)
        patched: dict[str, bytes] = {}
        for sheet, edits in by_sheet.items():
            path = paths[sheet]
            xml = original.read(path).decode("utf-8")
            xml = _expand_shared(xml, workbook, sheet, edits)
            for edit in edits:
                xml = _replace_cell(xml, edit["cell"], edit["replacement"])
            patched[path] = xml.encode("utf-8")
        book = original.read("xl/workbook.xml").decode("utf-8")
        book, count = re.subn(
            r"<calcPr\b([^>]*)/>",
            lambda m: (
                "<calcPr"
                + re.sub(
                    r'\s+(?:fullCalcOnLoad|forceFullCalc)="[^"]*"',
                    "",
                    m.group(1),
                )
                + ' fullCalcOnLoad="1" forceFullCalc="1"/>'
            ),
            book,
        )
        if count != 1:
            msg = "Cannot safely set workbook recalculation"
            raise ValueError(msg)
        patched["xl/workbook.xml"] = book.encode("utf-8")
        # A consumer may otherwise trust stale dependent formula caches despite
        # recalculation flags. Invalidate them in the copy, never in the source.
        for name in original.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                data = patched.get(name, original.read(name))
                patched[name] = _clear_formula_caches(data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output, ZipFile(output, "w") as result:
            result.comment = original.comment
            for entry in original.infolist():
                result.writestr(
                    entry,
                    patched.get(entry.filename, original.read(entry.filename)),
                )


def _expand_shared(
    xml: str,
    workbook: Workbook,
    sheet: str,
    edits: Sequence[Mapping[str, Any]],
) -> str:
    # Shared groups must be expanded as a unit: leaving a detached cell
    # inside a master's ref range can cause Excel to reuse the old formula.
    groups: set[str] = set()
    for edit in edits:
        match = _find_cell(xml, edit["cell"])
        if match:
            shared = re.search(
                r'<f\b[^>]*\bt="shared"[^>]*\bsi="(\d+)"',
                match.group(),
            )
            if shared:
                groups.add(shared.group(1))
    for group in groups:
        pattern = re.compile(
            r'<c\b[^>]*\br="([A-Z]+[0-9]+)"[^>]*[^/]>(?:(?!</?c\b).)*</c>',
        )
        for match in list(pattern.finditer(xml))[::-1]:
            cell_xml = match.group()
            formula = re.search(
                r'<f\b[^>]*\bt="shared"[^>]*\bsi="' + group + r'"[^>]*(?:/>|>.*?</f>)',
                cell_xml,
            )
            if formula is None:
                continue
            value = workbook[sheet][match.group(1)].value
            if not isinstance(value, str) or not value.startswith("="):
                msg = "Could not expand shared formula"
                raise ValueError(msg)
            replacement = "<f>" + escape(value[1:]) + "</f>"
            new_cell = (
                cell_xml[: formula.start()] + replacement + cell_xml[formula.end() :]
            )
            xml = xml[: match.start()] + new_cell + xml[match.end() :]

    return xml


def _find_cell(xml: str, coordinate: str) -> re.Match[str] | None:
    return re.search(
        r'<c\b[^>]*\br="' + re.escape(coordinate) + r'"[^>]*(?:/>|>.*?</c>)',
        xml,
    )


def _replace_cell(xml: str, coordinate: str, value: object) -> str:
    if isinstance(value, str) and value.startswith("="):
        content = "<f>" + escape(value[1:]) + "</f><v></v>"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        content = "<v>" + str(value) + "</v>"
    else:
        msg = "Only formula and numeric replacements are supported"
        raise ValueError(msg)
    match = _find_cell(xml, coordinate)
    if match:
        cell = match.group()
        opening = re.match(r"<c\b[^>]*", cell)
        if opening is None:
            msg = "Invalid cell XML"
            raise ValueError(msg)
        header = re.sub(r'\s+t="[^"]*"', "", opening.group()).rstrip("/")
        new_cell = header + ">" + content + "</c>"
        return xml[: match.start()] + new_cell + xml[match.end() :]
    column, row = coordinate_from_string(coordinate)
    row_match = re.search(r'<row\b[^>]*\br="' + str(row) + r'"[^>]*>.*?</row>', xml)
    if row_match is None:
        msg = "Target row is absent"
        raise ValueError(msg)
    row_xml = row_match.group()
    cells = list(
        re.finditer(r'<c\b[^>]*\br="([A-Z]+)[0-9]+"[^>]*(?:/>|>.*?</c>)', row_xml),
    )
    insert_at = next(
        (
            cell.start()
            for cell in cells
            if column_index_from_string(cell.group(1))
            > column_index_from_string(column)
        ),
        row_xml.rfind("</row>"),
    )
    new_cell = '<c r="' + coordinate + '">' + content + "</c>"
    return (
        xml[: row_match.start()]
        + row_xml[:insert_at]
        + new_cell
        + row_xml[insert_at:]
        + xml[row_match.end() :]
    )


def _clear_formula_caches(data: bytes) -> bytes:
    def clear(match: re.Match[bytes]) -> bytes:
        cell = match.group()
        if not re.search(rb"<f(?:\s|>)", cell):
            return cell
        return re.sub(rb"<v(?:\s[^>]*)?>.*?</v>", b"<v></v>", cell, flags=re.DOTALL)

    return re.sub(
        rb"<c\b[^>]*[^/]>(?:(?!</?c\b).)*</c>",
        clear,
        data,
        flags=re.DOTALL,
    )
