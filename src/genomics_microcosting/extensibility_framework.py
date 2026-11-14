# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Extensibility Framework for microcosting analysis.

This module provides a comprehensive framework for extending the microcosting analysis
with custom analyses, visualizations, and plugins.
"""

import importlib
import importlib.util
import json
import logging
from abc import abstractmethod
from dataclasses import InitVar, asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
lazy from collections.abc import Callable

from .data_manager import DataManager
from .logging_config import get_logger
from .plugin_system import Plugin, get_plugin_method

logger = get_logger(__name__)


@dataclass
class ExtensionMetadata:
    """Metadata for an extension."""

    name: str
    version: str
    description: str
    author: str
    license: str
    dependencies: list[str]
    tags: list[str]
    created_date: str
    last_updated: str
    extension_type: str  # 'analysis', 'visualization', 'report', 'data_processor', etc.


@dataclass(eq=False, repr=False, match_args=False)
class Extension(Plugin):
    """Base class for all extensions."""

    name: str
    version: str
    description: str
    author: InitVar[str] = ""
    license: InitVar[str] = ""
    dependencies: InitVar[list[str] | None] = None
    tags: InitVar[list[str] | None] = None
    extension_type: str = "generic"

    def __post_init__(
        self,
        author: str,
        plugin_license: str,
        dependencies: list[str] | None,
        tags: list[str] | None,
    ) -> None:
        """Initialize lifecycle state and record the supplied metadata."""
        super().__init__(self.name, self.version, self.description)
        self.metadata = ExtensionMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=author,
            license=plugin_license,
            dependencies=dependencies or [],
            tags=tags or [],
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            extension_type=self.extension_type,
        )
        self.initialized = False
        self.config: dict[str, Any] = {}
        self.data_manager: DataManager | None = None

    def set_data_manager(self, data_manager: DataManager) -> None:
        """Set the data manager for this extension.

        Args:
            data_manager: DataManager instance

        """
        self.data_manager = data_manager

    def set_config(self, config: dict[str, Any]) -> None:
        """Set extension configuration.

        Args:
            config: Configuration dictionary

        """
        self.config = config
        self.metadata.last_updated = datetime.now(UTC).isoformat()

    def get_config(self) -> dict[str, Any]:
        """Get extension configuration.

        Returns:
            Configuration dictionary

        """
        return self.config

    def export_metadata(self) -> dict[str, Any]:
        """Export extension metadata.

        Returns:
            Extension metadata as dictionary

        """
        return asdict(self.metadata)

    def validate_dependencies(self, available_extensions: list[str]) -> list[str]:
        """Validate extension dependencies.

        Args:
            available_extensions: List of available extension names

        Returns:
            List of missing dependencies

        """
        return [
            dep for dep in self.metadata.dependencies if dep not in available_extensions
        ]


@dataclass(eq=False, repr=False, match_args=False)
class AnalysisExtension(Extension):
    """Extension for custom analysis functionality."""

    extension_type: str = field(default="analysis", init=False)

    @abstractmethod
    def analyze(self, data: object, **kwargs: object) -> object:
        """Perform analysis on data.

        Args:
            data: Input data
            **kwargs: Additional analysis parameters

        Returns:
            Analysis results

        """
        message = "Subclasses must implement analyze method"
        raise NotImplementedError(message)


@dataclass(eq=False, repr=False, match_args=False)
class VisualizationExtension(Extension):
    """Extension for custom visualization functionality."""

    extension_type: str = field(default="visualization", init=False)

    @abstractmethod
    def visualize(self, data: object, **kwargs: object) -> object:
        """Create visualization of data.

        Args:
            data: Input data
            **kwargs: Additional visualization parameters

        Returns:
            Visualization object

        """
        message = "Subclasses must implement visualize method"
        raise NotImplementedError(message)


@dataclass(eq=False, repr=False, match_args=False)
class ReportExtension(Extension):
    """Extension for custom report generation functionality."""

    extension_type: str = field(default="report", init=False)

    @abstractmethod
    def generate_report(
        self,
        data: object,
        output_format: str = "markdown",
        **kwargs: object,
    ) -> str:
        """Generate report.

        Args:
            data: Input data
            output_format: Output format (markdown, html, pdf, etc.)
            **kwargs: Additional report parameters

        Returns:
            Generated report

        """
        message = "Subclasses must implement generate_report method"
        raise NotImplementedError(message)


@dataclass(eq=False, repr=False, match_args=False)
class DataProcessorExtension(Extension):
    """Extension for custom data processing functionality."""

    extension_type: str = field(default="data_processor", init=False)

    @abstractmethod
    def process(self, data: object, **kwargs: object) -> object:
        """Process data.

        Args:
            data: Input data
            **kwargs: Additional processing parameters

        Returns:
            Processed data

        """
        message = "Subclasses must implement process method"
        raise NotImplementedError(message)


class ExtensibilityFramework:
    """Framework for managing extensions and providing extensibility features."""

    def __init__(
        self,
        extension_directory: Path | None = None,
        config_file: Path | None = None,
    ) -> None:
        """Initialize the extensibility framework.

        Args:
            extension_directory: Directory to search for extensions
            config_file: Configuration file for extension settings

        """
        self.extensions: dict[str, Extension] = {}
        self.extension_directory = (
            extension_directory or Path(__file__).resolve().parents[0] / "extensions"
        )
        self.extension_directory.mkdir(exist_ok=True)
        self.config_file = config_file
        self.config: dict[str, Any] = {}
        self.data_manager: DataManager | None = None

        # Load configuration if provided
        if self.config_file and self.config_file.exists():
            self.load_config()

        logger.info(
            "ExtensibilityFramework initialized with directory: %s",
            self.extension_directory,
        )

    def set_data_manager(self, data_manager: DataManager) -> None:
        """Set the data manager for all extensions.

        Args:
            data_manager: DataManager instance

        """
        self.data_manager = data_manager
        # Set data manager for all existing extensions
        for extension in self.extensions.values():
            extension.set_data_manager(data_manager)

    def load_config(self) -> None:
        """Load framework configuration."""
        if self.config_file is None:
            return
        try:
            with self.config_file.open() as f:
                self.config = json.load(f)
            logger.info("Loaded configuration from %s", self.config_file)
        except Exception:
            logger.exception("Failed to load configuration")

    def save_config(self) -> None:
        """Save framework configuration."""
        if self.config_file:
            try:
                with Path(self.config_file).open("w") as f:
                    json.dump(self.config, f, indent=2)
                logger.info("Saved configuration to %s", self.config_file)
            except Exception:
                logger.exception("Failed to save configuration")

    def load_extension(self, extension_path: Path) -> Extension:
        """Load an extension from a file.

        Args:
            extension_path: Path to the extension file

        Returns:
            Loaded extension instance

        Raises:
            ImportError: If extension cannot be loaded

        """
        logger.info("Loading extension from %s", extension_path)

        # Load the module
        spec = importlib.util.spec_from_file_location(
            extension_path.stem,
            extension_path,
        )
        if spec is None or spec.loader is None:
            message = f"Cannot load extension from {extension_path}"
            raise ImportError(message)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the extension class (should be the only class that inherits from
        # Extension)
        extension_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Extension)
                and attr
                not in (
                    Extension,
                    AnalysisExtension,
                    VisualizationExtension,
                    ReportExtension,
                    DataProcessorExtension,
                )
            ):
                extension_class = attr
                break

        if extension_class is None:
            message = f"No valid extension class found in {extension_path}"
            raise ImportError(message)

        # Create extension instance
        try:
            extension_instance = cast("Callable[[], Extension]", extension_class)()
        except Exception as e:
            message = f"Failed to instantiate extension from {extension_path}: {e}"
            raise ImportError(
                message,
            ) from e

        # Set data manager if available
        if self.data_manager:
            extension_instance.set_data_manager(self.data_manager)

        logger.info(
            "Loaded extension: %s v%s",
            extension_instance.metadata.name,
            extension_instance.metadata.version,
        )
        return extension_instance

    def discover_extensions(self) -> list[Path]:
        """Discover extension files in the extension directory.

        Returns:
            List of extension file paths

        """
        extension_files = [
            file_path
            for file_path in self.extension_directory.glob("*.py")
            if file_path.name != "__init__.py"
        ]

        logger.info("Discovered %s extension files", len(extension_files))
        return extension_files

    def register_extension(self, extension: Extension) -> None:
        """Register an extension.

        Args:
            extension: Extension instance to register

        """
        if extension.metadata.name in self.extensions:
            logger.warning(
                "Extension %s already registered, replacing",
                extension.metadata.name,
            )

        self.extensions[extension.metadata.name] = extension
        logger.info("Registered extension: %s", extension.metadata.name)

    def load_all_extensions(self) -> None:
        """Load and register all extensions in the extension directory."""
        extension_files = self.discover_extensions()

        for extension_file in extension_files:
            try:
                extension = self.load_extension(extension_file)
                self.register_extension(extension)
                if extension.enabled:
                    extension.initialize()
            except Exception:
                logger.exception("Failed to load extension %s", extension_file)

    def get_extension(self, name: str) -> Extension | None:
        """Get a registered extension by name.

        Args:
            name: Extension name

        Returns:
            Extension instance or None if not found

        """
        return self.extensions.get(name)

    def list_extensions(self) -> list[dict[str, Any]]:
        """List all registered extensions.

        Returns:
            List of extension information

        """
        return [
            {
                "name": extension.metadata.name,
                "version": extension.metadata.version,
                "description": extension.metadata.description,
                "author": extension.metadata.author,
                "license": extension.metadata.license,
                "type": extension.metadata.extension_type,
                "tags": extension.metadata.tags,
                "enabled": extension.enabled,
            }
            for extension in self.extensions.values()
        ]

    def get_extensions_by_type(self, extension_type: str) -> list[Extension]:
        """Get extensions by type.

        Args:
            extension_type: Type of extensions to retrieve

        Returns:
            List of extensions of the specified type

        """
        return [
            extension
            for extension in self.extensions.values()
            if extension.metadata.extension_type == extension_type
        ]

    def validate_extension_dependencies(self) -> dict[str, list[str]]:
        """Validate dependencies for all extensions.

        Returns:
            Dictionary mapping extension names to lists of missing dependencies

        """
        available_extensions = list(self.extensions.keys())
        dependency_issues: dict[str, list[str]] = {}

        for name, extension in self.extensions.items():
            missing_deps = extension.validate_dependencies(available_extensions)
            if missing_deps:
                dependency_issues[name] = missing_deps

        return dependency_issues

    def execute_extension_method(
        self,
        extension_name: str,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> object:
        """Execute a method on an extension.

        Args:
            extension_name: Extension name
            method_name: Method name to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Method result

        Raises:
            ValueError: If extension not found or not enabled
            AttributeError: If the method is missing or is not callable

        """
        extension = self.get_extension(extension_name)
        if extension is None:
            message = f"Extension {extension_name} not found"
            raise ValueError(message)

        if not extension.enabled:
            message = f"Extension {extension_name} is not enabled"
            raise ValueError(message)

        method = get_plugin_method(extension, extension_name, "Extension", method_name)

        logger.info("Executing %s.%s", extension_name, method_name)
        return method(*args, **kwargs)

    def cleanup(self) -> None:
        """Clean up all extensions."""
        for extension in self.extensions.values():
            try:
                extension.cleanup()
            except Exception:
                logger.exception(
                    "Error cleaning up extension %s",
                    extension.metadata.name,
                )


# Example extension implementations
class ExampleAnalysisExtension(AnalysisExtension):
    """Example analysis extension."""

    def __init__(self) -> None:
        """Register metadata for the example analysis extension."""
        super().__init__(
            name="example_analysis_extension",
            version="1.0.0",
            description="Example analysis extension for demonstration",
            author="Microcosting Team",
            license="Apache-2.0",
        )

    def analyze(self, data: object, **_kwargs: object) -> object:
        """Perform example analysis."""
        logger.info("Performing example analysis")
        # This is just a placeholder - real analysis would go here
        return {
            "analysis_type": "example",
            "data_size": len(str(data)),
            "timestamp": datetime.now(UTC).isoformat(),
        }


class ExampleVisualizationExtension(VisualizationExtension):
    """Example visualization extension."""

    def __init__(self) -> None:
        """Register metadata for the example visualisation extension."""
        super().__init__(
            name="example_visualization_extension",
            version="1.0.0",
            description="Example visualization extension for demonstration",
            author="Microcosting Team",
            license="Apache-2.0",
        )

    def visualize(self, data: object, **_kwargs: object) -> object:
        """Create example visualization."""
        logger.info("Creating example visualization")
        # This is just a placeholder - real visualization would go here
        return {
            "visualization_type": "example",
            "data_size": len(str(data)),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# Example usage function
def example_usage() -> None:
    """Demonstrate the extensibility framework."""
    logger.info("%s", "Extensibility Framework Example")

    # Create data manager
    data_manager = DataManager()

    # Create extensibility framework
    framework = ExtensibilityFramework()
    framework.set_data_manager(data_manager)

    # Register example extensions
    analysis_extension = ExampleAnalysisExtension()
    viz_extension = ExampleVisualizationExtension()

    framework.register_extension(analysis_extension)
    framework.register_extension(viz_extension)

    # List extensions
    extensions = framework.list_extensions()
    logger.info("%s", f"Registered extensions: {len(extensions)}")
    for extension in extensions:
        logger.info(
            "%s",
            (
                f"  - {extension['name']} v{extension['version']}: "
                f"{extension['description']}"
            ),
        )

    # Execute extension methods
    try:
        result = framework.execute_extension_method(
            "example_analysis_extension",
            "analyze",
            "test data",
        )
        logger.info("%s", f"Analysis result: {result}")

        viz_result = framework.execute_extension_method(
            "example_visualization_extension",
            "visualize",
            "test data",
        )
        logger.info("%s", f"Visualization result: {viz_result}")
    except AttributeError, RuntimeError, TypeError, ValueError:
        logger.exception("Error executing extension method")

    # Cleanup
    framework.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
