# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Data pipeline for genomics microcosting.

This module implements a modular data processing pipeline using the
Extractor → Transformer → Loader (ETL) pattern for flexible and
extensible data processing workflows.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeGuard

import polars as pl

lazy from .data_manager import DataManager

logger = logging.getLogger(__name__)

type Tables = pl.DataFrame | dict[str, pl.DataFrame]
type PipelineData = Tables | list[Tables] | list[PipelineData]


def _are_frames(data: list[PipelineData]) -> TypeGuard[list[pl.DataFrame]]:
    return all(isinstance(item, pl.DataFrame) for item in data)


class PipelineComponent[Input, Output](ABC):
    """Abstract base class for all pipeline components."""

    def __init__(self, name: str) -> None:
        """Set the component name and initialise its logger."""
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def process(self, data: Input) -> Output:
        """Process the input data and return the result."""

    def validate_input(self, data: Input) -> bool:
        """Validate input data. Override in subclasses as needed."""
        del data
        return True

    def validate_output(self, data: Output) -> bool:
        """Validate output data. Override in subclasses as needed."""
        del data
        return True


class Extractor(PipelineComponent[object, PipelineData]):
    """Abstract base class for data extraction components."""

    def __init__(self, name: str, source_path: str | Path) -> None:
        """Set the component name and source path."""
        super().__init__(name)
        self.source_path = Path(source_path)

    @abstractmethod
    def extract(self) -> PipelineData:
        """Extract data from the source."""

    def process(self, data: object = None) -> PipelineData:
        """Extract data from source (data parameter ignored for extractors)."""
        del data
        return self.extract()


class PreparedSheetExtractor(Extractor):
    """Read a typed prepared sheet through the native DataManager API."""

    def __init__(self, name: str, manager: DataManager, sheet_name: str) -> None:
        """Bind the data manager and prepared sheet name."""
        super().__init__(name, manager.prepared_dir)
        self.manager = manager
        self.sheet_name = sheet_name

    def extract(self) -> pl.DataFrame:
        """Return the exact native table or report a missing source explicitly."""
        frame = self.manager.load_sheet(self.sheet_name)
        if frame is None:
            message = f"Prepared sheet not found: {self.sheet_name}"
            raise FileNotFoundError(message)
        return frame


class Transformer(PipelineComponent[Tables, Tables]):
    """Abstract base class for data transformation components."""

    def __init__(self, name: str) -> None:
        """Initialise the named transformation component."""
        super().__init__(name)

    @abstractmethod
    def transform(self, data: Tables) -> Tables:
        """Transform the input data."""

    def process(self, data: Tables) -> Tables:
        """Transform the input data."""
        if not self.validate_input(data):
            message = f"Invalid input data for transformer {self.name}"
            raise ValueError(message)
        result = self.transform(data)
        if not self.validate_output(result):
            message = f"Invalid output data from transformer {self.name}"
            raise ValueError(message)
        return result


class Loader(PipelineComponent[Tables, Tables]):
    """Abstract base class for data loading components."""

    def __init__(self, name: str, target_path: str | Path) -> None:
        """Set the component name and output path."""
        super().__init__(name)
        self.target_path = Path(target_path)

    @abstractmethod
    def load(self, data: Tables) -> None:
        """Load data to the target destination."""

    def process(self, data: Tables) -> Tables:
        """Load data and return the data unchanged."""
        if not self.validate_input(data):
            message = f"Invalid input data for loader {self.name}"
            raise ValueError(message)
        self.load(data)
        return data


class DataPipeline:
    """Main data pipeline class that orchestrates ETL operations."""

    def __init__(self, name: str) -> None:
        """Create an empty pipeline with the given name."""
        self.name = name
        self.extractors: list[Extractor] = []
        self.transformers: list[Transformer] = []
        self.loaders: list[Loader] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def add_extractor(self, extractor: Extractor) -> None:
        """Add an extractor to the pipeline."""
        self.extractors.append(extractor)
        self.logger.debug("Added extractor: %s", extractor.name)

    def add_transformer(self, transformer: Transformer) -> None:
        """Add a transformer to the pipeline."""
        self.transformers.append(transformer)
        self.logger.debug("Added transformer: %s", transformer.name)

    def add_loader(self, loader: Loader) -> None:
        """Add a loader to the pipeline."""
        self.loaders.append(loader)
        self.logger.debug("Added loader: %s", loader.name)

    def run(self) -> PipelineData:
        """Execute the complete pipeline."""
        self.logger.info("Starting pipeline: %s", self.name)

        pipeline_data = self._extract_data()
        if isinstance(pipeline_data, list):
            if self.transformers or self.loaders:
                message = "Transformers and loaders require a table or named tables"
                raise TypeError(message)
            self.logger.info("Pipeline %s completed successfully", self.name)
            return pipeline_data

        # Transform phase
        for transformer in self.transformers:
            self.logger.debug("Running transformer: %s", transformer.name)
            try:
                pipeline_data = transformer.process(pipeline_data)
            except Exception:
                self.logger.exception("Transformer %s failed", transformer.name)
                raise

        # Load phase
        for loader in self.loaders:
            self.logger.debug("Running loader: %s", loader.name)
            try:
                loader.process(pipeline_data)
            except Exception:
                self.logger.exception("Loader %s failed", loader.name)
                raise

        self.logger.info("Pipeline %s completed successfully", self.name)
        return pipeline_data

    def _extract_data(self) -> PipelineData:
        extracted_data: list[PipelineData] = []
        for extractor in self.extractors:
            self.logger.debug("Running extractor: %s", extractor.name)
            try:
                data = extractor.process()
                extracted_data.append(data)
            except Exception:
                self.logger.exception("Extractor %s failed", extractor.name)
                raise

        if len(extracted_data) == 1:
            return extracted_data[0]
        if _are_frames(extracted_data):
            return pl.concat(extracted_data, how="diagonal")
        return extracted_data

    def validate_pipeline(self) -> bool:
        """Validate that the pipeline is properly configured."""
        if not self.extractors:
            self.logger.warning("Pipeline has no extractors")
            return False

        if not self.loaders:
            self.logger.warning("Pipeline has no loaders")
            return False

        return True
