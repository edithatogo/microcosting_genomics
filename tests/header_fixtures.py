# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Minimal workbook header records, independent of any dataframe backend."""

from collections.abc import Iterator, Mapping, Sequence


class HeaderFixture:
    """Supply duplicate or multilevel header labels and unchanged row values."""

    def __init__(
        self,
        data: Mapping[str, Sequence[object]] | Sequence[Sequence[object]] | None = None,
        *,
        columns: Sequence[object] | None = None,
    ) -> None:
        """Retain row order while rejecting inconsistent fixture shapes."""
        if isinstance(data, Mapping):
            self.columns: Sequence[object] = list(data) if columns is None else columns
            self.rows = list(zip(*data.values(), strict=True))
        else:
            self.rows = [tuple(row) for row in data] if data is not None else []
            self.columns = [] if columns is None else columns
        if any(len(row) != len(self.columns) for row in self.rows):
            message = "Fixture row/header widths differ"
            raise ValueError(message)

    def itertuples(self, *, index: bool, name: None) -> Iterator[tuple[object, ...]]:
        """Expose the structural workbook-row contract consumed by DataManager."""
        del name
        if index:
            message = "Header fixtures expose source values without a synthetic index"
            raise ValueError(message)
        return iter(self.rows)
