"""
Loader Components for Genomics Microcosting Data Pipeline

This module contains concrete implementations of loader components
for saving processed data to various destinations and formats.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import json

import pandas as pd

from .data_pipeline import Loader


class ParquetLoader(Loader):
    """Loader for saving data to Parquet format."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 **kwargs):
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save data to Parquet format."""
        if isinstance(data, dict):
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = self.target_path / f"{sheet_name}.parquet"
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.parquet"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pd.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to Parquet."""
        try:
            df.to_parquet(file_path, **self.kwargs)
            self.logger.info(f"Saved DataFrame to {file_path} ({len(df)} rows, {len(df.columns)} columns)")
        except Exception as e:
            self.logger.error(f"Failed to save DataFrame to {file_path}: {e}")
            raise


class CSVLoader(Loader):
    """Loader for saving data to CSV format."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 **kwargs):
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save data to CSV format."""
        if isinstance(data, dict):
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = self.target_path / f"{sheet_name}.csv"
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.csv"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pd.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to CSV."""
        try:
            df.to_csv(file_path, **self.kwargs)
            self.logger.info(f"Saved DataFrame to {file_path} ({len(df)} rows, {len(df.columns)} columns)")
        except Exception as e:
            self.logger.error(f"Failed to save DataFrame to {file_path}: {e}")
            raise


class JSONLoader(Loader):
    """Loader for saving data to JSON format."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 **kwargs):
        super().__init__(name, target_path)
        self.kwargs = kwargs
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save data to JSON format."""
        if isinstance(data, dict):
            # Handle multiple sheets
            for sheet_name, df in data.items():
                file_path = self.target_path / f"{sheet_name}.json"
                self._save_dataframe(df, file_path)
        else:
            # Handle single DataFrame
            if self.target_path.is_dir():
                file_path = self.target_path / "data.json"
            else:
                file_path = self.target_path
            self._save_dataframe(data, file_path)

    def _save_dataframe(self, df: pd.DataFrame, file_path: Path) -> None:
        """Save a single DataFrame to JSON."""
        try:
            # Convert DataFrame to JSON-serializable format
            json_data = df.to_dict(orient='records')

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, **self.kwargs)

            self.logger.info(f"Saved DataFrame to {file_path} ({len(df)} rows, {len(df.columns)} columns)")
        except Exception as e:
            self.logger.error(f"Failed to save DataFrame to {file_path}: {e}")
            raise


class MultiFormatLoader(Loader):
    """Loader that can save data to multiple formats simultaneously."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 formats: Optional[List[str]] = None,
                 **kwargs):
        super().__init__(name, target_path)
        if formats is None:
            formats = ['parquet', 'csv']
        self.formats = formats
        self.kwargs = kwargs

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save data to multiple formats."""
        for fmt in self.formats:
            if fmt == 'parquet':
                loader = ParquetLoader(f"{self.name}_parquet", self.target_path, **self.kwargs)
            elif fmt == 'csv':
                loader = CSVLoader(f"{self.name}_csv", self.target_path, **self.kwargs)
            elif fmt == 'json':
                loader = JSONLoader(f"{self.name}_json", self.target_path, **self.kwargs)
            else:
                self.logger.warning(f"Unsupported format: {fmt}")
                continue

            try:
                loader.load(data)
            except Exception as e:
                self.logger.error(f"Failed to save in {fmt} format: {e}")


class DatabaseLoader(Loader):
    """Loader for saving data to a database (placeholder for future implementation)."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 connection_string: Optional[str] = None,
                 table_name: Optional[str] = None,
                 **kwargs):
        super().__init__(name, target_path)
        self.connection_string = connection_string
        self.table_name = table_name or "genomics_data"
        self.kwargs = kwargs

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save data to database (placeholder implementation)."""
        self.logger.info("Database loading not yet implemented - this is a placeholder")

        # TODO: Implement actual database loading
        # This would use SQLAlchemy or similar to save to a database

        if isinstance(data, dict):
            for sheet_name, df in data.items():
                self.logger.info(f"Would save {sheet_name} to database table {self.table_name}_{sheet_name}")
        else:
            self.logger.info(f"Would save data to database table {self.table_name}")


class MetadataLoader(Loader):
    """Loader for saving metadata about the data processing."""

    def __init__(self,
                 name: str,
                 target_path: Union[str, Path],
                 include_validation: bool = True):
        super().__init__(name, target_path)
        self.include_validation = include_validation
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> None:
        """Save metadata about the processed data."""
        metadata = {
            'processing_timestamp': pd.Timestamp.now().isoformat(),
            'pipeline_name': self.name,
            'data_info': {}
        }

        if isinstance(data, dict):
            for sheet_name, df in data.items():
                metadata['data_info'][sheet_name] = self._get_dataframe_info(df)
        else:
            metadata['data_info']['data'] = self._get_dataframe_info(data)

        # Save metadata to JSON file
        metadata_path = self.target_path / "metadata.json"
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
            self.logger.info(f"Saved metadata to {metadata_path}")
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")

    def _get_dataframe_info(self, df: pd.DataFrame) -> Dict:
        """Get information about a DataFrame."""
        info = {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'memory_usage': df.memory_usage(deep=True).sum()
        }

        # Include validation results if available
        if self.include_validation and hasattr(df, 'attrs') and 'validation_results' in df.attrs:
            info['validation_results'] = df.attrs['validation_results']

        return info