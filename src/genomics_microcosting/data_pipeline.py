"""
Data Pipeline Module for Genomics Microcosting

This module implements a modular data processing pipeline using the
Extractor → Transformer → Loader (ETL) pattern for flexible and
extensible data processing workflows.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class PipelineComponent(ABC):
    """Abstract base class for all pipeline components."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process the input data and return the result."""
        pass

    def validate_input(self, data: Any) -> bool:
        """Validate input data. Override in subclasses as needed."""
        return True

    def validate_output(self, data: Any) -> bool:
        """Validate output data. Override in subclasses as needed."""
        return True


class Extractor(PipelineComponent):
    """Abstract base class for data extraction components."""

    def __init__(self, name: str, source_path: Union[str, Path]):
        super().__init__(name)
        self.source_path = Path(source_path)

    @abstractmethod
    def extract(self) -> Any:
        """Extract data from the source."""
        pass

    def process(self, data: Any = None) -> Any:
        """Extract data from source (data parameter ignored for extractors)."""
        return self.extract()


class Transformer(PipelineComponent):
    """Abstract base class for data transformation components."""

    def __init__(self, name: str):
        super().__init__(name)

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Transform the input data."""
        pass

    def process(self, data: Any) -> Any:
        """Transform the input data."""
        if not self.validate_input(data):
            raise ValueError(f"Invalid input data for transformer {self.name}")
        result = self.transform(data)
        if not self.validate_output(result):
            raise ValueError(f"Invalid output data from transformer {self.name}")
        return result


class Loader(PipelineComponent):
    """Abstract base class for data loading components."""

    def __init__(self, name: str, target_path: Union[str, Path]):
        super().__init__(name)
        self.target_path = Path(target_path)

    @abstractmethod
    def load(self, data: Any) -> None:
        """Load data to the target destination."""
        pass

    def process(self, data: Any) -> Any:
        """Load data and return the data unchanged."""
        if not self.validate_input(data):
            raise ValueError(f"Invalid input data for loader {self.name}")
        self.load(data)
        return data


class DataPipeline:
    """Main data pipeline class that orchestrates ETL operations."""

    def __init__(self, name: str):
        self.name = name
        self.extractors: List[Extractor] = []
        self.transformers: List[Transformer] = []
        self.loaders: List[Loader] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def add_extractor(self, extractor: Extractor) -> None:
        """Add an extractor to the pipeline."""
        self.extractors.append(extractor)
        self.logger.debug(f"Added extractor: {extractor.name}")

    def add_transformer(self, transformer: Transformer) -> None:
        """Add a transformer to the pipeline."""
        self.transformers.append(transformer)
        self.logger.debug(f"Added transformer: {transformer.name}")

    def add_loader(self, loader: Loader) -> None:
        """Add a loader to the pipeline."""
        self.loaders.append(loader)
        self.logger.debug(f"Added loader: {loader.name}")

    def run(self) -> Any:
        """Execute the complete pipeline."""
        self.logger.info(f"Starting pipeline: {self.name}")

        # Extract phase
        extracted_data = []
        for extractor in self.extractors:
            self.logger.debug(f"Running extractor: {extractor.name}")
            try:
                data = extractor.process()
                extracted_data.append(data)
            except Exception as e:
                self.logger.error(f"Extractor {extractor.name} failed: {e}")
                raise

        # Combine extracted data if multiple extractors
        if len(extracted_data) == 1:
            pipeline_data = extracted_data[0]
        else:
            # For now, assume we want to combine DataFrames
            if all(isinstance(d, pd.DataFrame) for d in extracted_data):
                pipeline_data = pd.concat(extracted_data, ignore_index=True)
            else:
                pipeline_data = extracted_data

        # Transform phase
        for transformer in self.transformers:
            self.logger.debug(f"Running transformer: {transformer.name}")
            try:
                pipeline_data = transformer.process(pipeline_data)
            except Exception as e:
                self.logger.error(f"Transformer {transformer.name} failed: {e}")
                raise

        # Load phase
        for loader in self.loaders:
            self.logger.debug(f"Running loader: {loader.name}")
            try:
                loader.process(pipeline_data)
            except Exception as e:
                self.logger.error(f"Loader {loader.name} failed: {e}")
                raise

        self.logger.info(f"Pipeline {self.name} completed successfully")
        return pipeline_data

    def validate_pipeline(self) -> bool:
        """Validate that the pipeline is properly configured."""
        if not self.extractors:
            self.logger.warning("Pipeline has no extractors")
            return False

        if not self.loaders:
            self.logger.warning("Pipeline has no loaders")
            return False

        return True