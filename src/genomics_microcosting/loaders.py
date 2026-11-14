# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Loader components for the genomics microcosting data pipeline.

This module contains concrete implementations of loader components
for saving processed data to various destinations and formats.
"""

import json
from datetime import UTC, datetime
from typing import NotRequired, TypedDict, TypeGuard, Unpack
lazy from collections.abc import Mapping
lazy from pathlib import Path

from pydantic import ConfigDict, TypeAdapter
from pydantic import ValidationError as OptionValidationError
lazy import polars as pl

from .data_manager import DataManager
from .data_pipeline import Loader
from .loader_options import (
    CSV_OPTIONS,
    JSON_OPTIONS,
    PARQUET_OPTIONS,
    CSVOptions,
    JSONOptions,
    ParquetOptions,
)


class DataFrameInfo(TypedDict):
    """Observed native table metadata without changing values or schemas."""

    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    memory_usage: int | float
    validation_results: NotRequired[dict[str, object]]


class PipelineMetadata(TypedDict):
    """The existing JSON metadata document saved for a pipeline run."""

    processing_timestamp: str
    pipeline_name: str
    data_info: dict[str, DataFrameInfo]


def _validate_sheet_names(data: Mapping[str, pl.DataFrame]) -> None:
    """Reject ambiguous filenames before writing any source sheet."""
    names = [DataManager.sanitize_sheet_name(name) for name in data]
    if any(not name for name in names) or len(set(names)) != len(names):
        message = "Source sheet names collide after filename normalisation"
        raise ValueError(message)


class ParquetLoader(Loader):
    """Loader for saving data to Parquet format."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        **kwargs: Unpack[ParquetOptions],
    ) -> None:
        """Configure the destination and preserve this loader's writer options."""
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save data to Parquet format."""
        if isinstance(data, dict):
            _validate_sheet_names(data)
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = (
                    self.target_path
                    / f"{DataManager.sanitize_sheet_name(sheet_name)}.parquet"
                )
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.parquet"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pl.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to Parquet."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.write_parquet(file_path, **self.kwargs)
            self.logger.info(
                "Saved DataFrame to %s (%s rows, %s columns)",
                file_path,
                len(df),
                len(df.columns),
            )
        except Exception:
            self.logger.exception("Failed to save DataFrame to %s", file_path)
            raise


class CSVLoader(Loader):
    """Loader for saving data to CSV format."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        **kwargs: Unpack[CSVOptions],
    ) -> None:
        """Configure the destination and preserve this loader's writer options."""
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save data to CSV format."""
        if isinstance(data, dict):
            _validate_sheet_names(data)
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = (
                    self.target_path
                    / f"{DataManager.sanitize_sheet_name(sheet_name)}.csv"
                )
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.csv"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pl.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to CSV."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.write_csv(file_path, **self.kwargs)
            self.logger.info(
                "Saved DataFrame to %s (%s rows, %s columns)",
                file_path,
                len(df),
                len(df.columns),
            )
        except Exception:
            self.logger.exception("Failed to save DataFrame to %s", file_path)
            raise


class JSONLoader(Loader):
    """Loader for saving data to JSON format."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        **kwargs: Unpack[JSONOptions],
    ) -> None:
        """Configure the destination and preserve this loader's writer options."""
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save data to JSON format."""
        if isinstance(data, dict):
            _validate_sheet_names(data)
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = (
                    self.target_path
                    / f"{DataManager.sanitize_sheet_name(sheet_name)}.json"
                )
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.json"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pl.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to JSON."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Convert DataFrame to JSON-serializable format
            json_data = df.to_dicts()

            with file_path.open("w", encoding="utf-8") as f:
                options: JSONOptions = {"default": str, **self.kwargs}
                json.dump(json_data, f, indent=2, **options)

            self.logger.info(
                "Saved DataFrame to %s (%s rows, %s columns)",
                file_path,
                len(df),
                len(df.columns),
            )
        except Exception:
            self.logger.exception("Failed to save DataFrame to %s", file_path)
            raise


class MultiFormatLoader(Loader):
    """Loader that can save data to multiple formats simultaneously."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        formats: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        """Configure the destination and preserve this loader's writer options."""
        super().__init__(name, target_path)
        if formats is None:
            formats = ["parquet", "csv"]
        self.formats = formats
        self.kwargs = kwargs
        self.target_path.mkdir(parents=True, exist_ok=True)

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save data to multiple formats."""
        failures: list[str] = []
        for fmt in self.formats:
            try:
                if fmt == "parquet":
                    loader = ParquetLoader(
                        f"{self.name}_parquet",
                        self.target_path,
                        **PARQUET_OPTIONS.validate_python(self.kwargs),
                    )
                elif fmt == "csv":
                    loader = CSVLoader(
                        f"{self.name}_csv",
                        self.target_path,
                        **CSV_OPTIONS.validate_python(self.kwargs),
                    )
                elif fmt == "json":
                    loader = JSONLoader(
                        f"{self.name}_json",
                        self.target_path,
                        **JSON_OPTIONS.validate_python(self.kwargs),
                    )
                else:
                    failures.append(fmt)
                    continue
                loader.load(data)
            except Exception:
                self.logger.exception("Failed to save in %s format", fmt)
                failures.append(fmt)

        if failures:
            message = f"Requested formats failed: {failures}"
            raise RuntimeError(message)


class DatabaseLoader(Loader):
    """Loader for saving data to a database (placeholder for future implementation)."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        connection_string: str | None = None,
        table_name: str | None = None,
        **kwargs: object,
    ) -> None:
        """Configure the destination and preserve this loader's writer options."""
        super().__init__(name, target_path)
        self.connection_string = connection_string
        self.table_name = table_name or "genomics_data"
        self.kwargs = kwargs

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save data to database (placeholder implementation)."""
        self.logger.info("Database loading not yet implemented - this is a placeholder")

        # Database persistence remains unimplemented; this path writes no state.
        # This would use SQLAlchemy or similar to save to a database

        if isinstance(data, dict):
            for sheet_name in data:
                self.logger.info(
                    "Would save %s to database table %s_%s",
                    sheet_name,
                    self.table_name,
                    sheet_name,
                )
        else:
            self.logger.info("Would save data to database table %s", self.table_name)


class MetadataOptions(TypedDict, total=False):
    """Named metadata settings with a retained positional compatibility boundary."""

    include_validation: bool
    validation_results: Mapping[str, object] | None


_STRING_MAPPING = TypeAdapter(dict[str, object], config=ConfigDict(strict=True))
_METADATA_KEYS = ("include_validation", "validation_results")


def _is_string_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    """Validate legacy keys while retaining the original live mapping object."""
    if not isinstance(value, Mapping):
        return False
    try:
        _STRING_MAPPING.validate_python(value)
    except OptionValidationError:
        return False
    return True


def _metadata_arguments(
    legacy: tuple[object, ...],
    settings: MetadataOptions,
) -> tuple[bool, Mapping[str, object] | None]:
    """Preserve valid positional calls and Python's duplicate-argument failures."""
    if len(legacy) > len(_METADATA_KEYS):
        message = "MetadataLoader accepts at most two optional positional settings"
        raise TypeError(message)
    for key in _METADATA_KEYS[: len(legacy)]:
        if key in settings:
            message = f"MetadataLoader received multiple values for {key}"
            raise TypeError(message)
    include_validation = settings.get("include_validation", True)
    validation_results = settings.get("validation_results")
    if legacy:
        flag = legacy[0]
        if not isinstance(flag, bool):
            message = "The positional validation setting must be boolean"
            raise TypeError(message)
        include_validation = flag
    if len(legacy) == len(_METADATA_KEYS):
        result = legacy[1]
        if result is not None and not _is_string_mapping(result):
            message = "Validation results must be a string-keyed mapping or null"
            raise TypeError(message)
        validation_results = result
    return include_validation, validation_results


class MetadataLoader(Loader):
    """Loader for saving metadata about the data processing."""

    def __init__(
        self,
        name: str,
        target_path: str | Path,
        *legacy_settings: object,
        **settings: Unpack[MetadataOptions],
    ) -> None:
        """Prefer named settings while preserving valid legacy positional calls."""
        super().__init__(name, target_path)
        self.include_validation, self.validation_results = _metadata_arguments(
            legacy_settings,
            settings,
        )
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: pl.DataFrame | dict[str, pl.DataFrame]) -> None:
        """Save metadata about the processed data."""
        metadata: PipelineMetadata = {
            "processing_timestamp": datetime.now(UTC).isoformat(),
            "pipeline_name": self.name,
            "data_info": {},
        }

        if isinstance(data, dict):
            for sheet_name, df in data.items():
                metadata["data_info"][sheet_name] = self._get_dataframe_info(df)
        else:
            metadata["data_info"]["data"] = self._get_dataframe_info(data)

        # Save metadata to JSON file
        metadata_path = self.target_path / "metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
            self.logger.info("Saved metadata to %s", metadata_path)
        except Exception:
            self.logger.exception("Failed to save metadata")
            raise

    def _get_dataframe_info(self, df: pl.DataFrame) -> DataFrameInfo:
        """Get information about a DataFrame."""
        info: DataFrameInfo = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.schema.items()},
            "memory_usage": df.estimated_size(),
        }

        if self.include_validation and self.validation_results is not None:
            info["validation_results"] = dict(self.validation_results)

        return info
