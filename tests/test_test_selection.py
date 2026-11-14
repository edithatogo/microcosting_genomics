# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Ensure local test selection never mistakes shared changes for no tests."""

import pytest

from tools.select_tests import select_tests


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["README.md"], []),
        (["tests/test_cost_properties.py"], ["tests/test_cost_properties.py"]),
        (["uv.lock"], ["tests"]),
        (["tests/conftest.py"], ["tests"]),
        (["tests/header_fixtures.py"], ["tests"]),
        (["tests/test_data/scenarios.py"], ["tests"]),
        (["scripts/parse_cost_tables.py"], ["tests"]),
        (["src/genomics_microcosting/__init__.py"], ["tests"]),
        (["tools/select_tests.py"], ["tests"]),
    ],
)
def test_selection_boundaries(paths: list[str], expected: list[str]) -> None:
    """Preserve exact test selection and conservative milestone fallbacks."""
    if select_tests(paths) != expected:
        raise AssertionError((paths, select_tests(paths)))


def test_source_dependency_selection() -> None:
    """Include existing direct users of the modified formula parser."""
    selected = select_tests(["src/genomics_microcosting/formula_parser.py"])
    if "tests/test_formula_parser.py" not in selected and selected != ["tests"]:
        raise AssertionError(selected)
