# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Typed native writer options qualified against the locked Polars signatures."""

from collections.abc import Callable, Sequence
from typing import Literal, Protocol, TypedDict, runtime_checkable
lazy import json

from pydantic import ConfigDict, TypeAdapter, with_config
lazy import polars as pl
lazy from polars._typing import ParquetMetadataContext


@runtime_checkable
class ArrowSchemaProvider(Protocol):
    """The structural Arrow C schema interface consumed by Polars."""

    def __arrow_c_schema__(self) -> object:
        """Return the schema capsule without changing the source table."""
        ...


type CredentialCallback = Callable[[], tuple[dict[str, str], int | None]]
type Compression = Literal["lz4", "uncompressed", "snappy", "gzip", "brotli", "zstd"]


@with_config(ConfigDict(strict=True, extra="forbid", arbitrary_types_allowed=True))
class ParquetOptions(TypedDict, total=False):
    """Forward the complete installed native Parquet keyword interface."""

    compression: Compression
    compression_level: int | None
    statistics: bool | str | dict[str, bool]
    row_group_size: int | None
    data_page_size: int | None
    use_pyarrow: bool
    pyarrow_options: dict[str, object] | None
    partition_by: str | Sequence[str] | None
    partition_chunk_size_bytes: int
    storage_options: dict[str, object] | None
    credential_provider: CredentialCallback | Literal["auto"] | None
    metadata: dict[str, str] | Callable[[ParquetMetadataContext], dict[str, str]] | None
    arrow_schema: ArrowSchemaProvider | None
    encryption: pl.ParquetEncryptionProperties | None
    mkdir: bool


@with_config(ConfigDict(strict=True, extra="forbid"))
class CSVOptions(TypedDict, total=False):
    """Forward the complete installed native CSV keyword interface."""

    include_bom: bool
    compression: Literal["uncompressed", "gzip", "zstd"]
    compression_level: int | None
    check_extension: bool
    include_header: bool
    separator: str
    line_terminator: str
    quote_char: str
    batch_size: int
    datetime_format: str | None
    date_format: str | None
    time_format: str | None
    float_scientific: bool | None
    float_precision: int | None
    decimal_comma: bool
    null_value: str | None
    quote_style: Literal["necessary", "always", "non_numeric", "never"] | None
    storage_options: dict[str, object] | None
    credential_provider: CredentialCallback | Literal["auto"] | None


@with_config(ConfigDict(strict=True, arbitrary_types_allowed=True))
class JSONOptions(TypedDict, total=False, extra_items=object):
    """Retain JSON dump options while the loader owns its existing indentation."""

    skipkeys: bool
    ensure_ascii: bool
    check_circular: bool
    allow_nan: bool
    cls: type[json.JSONEncoder] | None
    separators: tuple[str, str] | None
    default: Callable[[object], object] | None
    sort_keys: bool


PARQUET_OPTIONS = TypeAdapter(ParquetOptions)
CSV_OPTIONS = TypeAdapter(CSVOptions)
JSON_OPTIONS = TypeAdapter(JSONOptions)
