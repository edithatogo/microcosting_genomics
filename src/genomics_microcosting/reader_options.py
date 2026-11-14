# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Keyword contracts matching the locked native Polars readers."""

from typing import Literal, TypedDict
lazy from collections.abc import Callable, Sequence

lazy import polars as pl
lazy from polars._typing import ParallelStrategy, PolarsDataType, SchemaDict

lazy from .loader_options import CredentialCallback


class CSVReadOptions(TypedDict, total=False):
    """Retain every supported native reader keyword without implicit conversion."""

    columns: Sequence[int] | Sequence[str] | None
    has_header: bool
    separator: str
    comment_prefix: str | None
    quote_char: str | None
    skip_rows: int
    skip_lines: int
    schema: SchemaDict | None
    schema_overrides: SchemaDict | Sequence[PolarsDataType] | None
    null_values: str | Sequence[str] | dict[str, str] | None
    empty_string_is_null: bool
    ignore_errors: bool
    with_column_names: Callable[[list[str]], list[str]] | None
    infer_schema: bool
    infer_schema_length: int | None
    infer_schema_files: int
    n_rows: int | None
    encoding: str
    low_memory: bool
    skip_rows_after_header: int
    row_index_name: str | None
    row_index_offset: int
    try_parse_dates: bool
    eol_char: str
    new_columns: Sequence[str] | None
    truncate_ragged_lines: bool | None
    raise_if_empty: bool | None
    decimal_comma: bool
    glob: bool
    storage_options: dict[str, object] | None
    credential_provider: CredentialCallback | Literal["auto"] | None
    include_file_paths: str | None
    extra_columns: Literal["ignore", "raise"] | None
    missing_columns: Literal["insert", "raise"] | None
    use_pyarrow: bool


class ParquetReadOptions(TypedDict, total=False):
    """Retain every supported native reader keyword without implicit conversion."""

    columns: list[int] | list[str] | None
    n_rows: int | None
    row_index_name: str | None
    row_index_offset: int
    parallel: ParallelStrategy
    use_statistics: bool
    hive_partitioning: bool | None
    glob: bool
    schema: SchemaDict | None
    hive_schema: SchemaDict | None
    try_parse_hive_dates: bool
    low_memory: bool
    storage_options: dict[str, object] | None
    credential_provider: CredentialCallback | Literal["auto"] | None
    use_pyarrow: bool
    pyarrow_options: dict[str, object] | None
    memory_map: bool
    include_file_paths: str | None
    missing_columns: Literal["insert", "raise"]
    decryption: pl.ParquetDecryptionProperties | None
    _expand_paths: bool
