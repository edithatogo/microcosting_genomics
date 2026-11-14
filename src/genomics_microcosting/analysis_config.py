# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Configuration-driven Analysis Parameters System.

This module provides a comprehensive system for managing analysis parameters
through configuration files, enabling flexible and customizable analyses.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import yaml
from pydantic import ConfigDict, TypeAdapter, with_config

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AnalysisParameter:
    """Represents a single analysis parameter."""

    name: str
    value: object
    description: str
    data_type: str  # 'int', 'float', 'str', 'bool', 'list', 'dict'
    default_value: object
    min_value: int | float | None = None
    max_value: int | float | None = None
    choices: list[object] | None = None
    required: bool = True
    category: str = "general"


@dataclass
class AnalysisConfig:
    """Configuration for a specific analysis type."""

    analysis_type: str
    version: str
    description: str
    parameters: dict[str, AnalysisParameter]
    created_date: str
    last_updated: str
    author: str = ""
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Normalize missing tags for older configurations."""
        if self.tags is None:
            self.tags = []


class _SavedParameter(TypedDict):
    name: str
    value: object
    description: str
    data_type: str
    default_value: object


class _ParameterDocument(_SavedParameter, total=False):
    min_value: int | float | None
    max_value: int | float | None
    choices: list[object] | None
    required: bool
    category: str


class _SavedAnalysisConfig(TypedDict):
    analysis_type: str
    version: str
    description: str
    created_date: str
    last_updated: str


@with_config(ConfigDict(strict=True))
class _AnalysisConfigDocument(_SavedAnalysisConfig, total=False):
    parameters: dict[str, _ParameterDocument]
    author: str
    tags: list[str] | None


_ANALYSIS_CONFIG_DOCUMENT = TypeAdapter(_AnalysisConfigDocument)


def load_analysis_configuration(document: object) -> AnalysisConfig:
    """Validate configuration metadata and reconstruct its parameters."""
    fields = _ANALYSIS_CONFIG_DOCUMENT.validate_python(document)
    parameters = {
        name: AnalysisParameter(**value)
        for name, value in fields.get("parameters", {}).items()
    }
    return AnalysisConfig(
        analysis_type=fields["analysis_type"],
        version=fields["version"],
        description=fields["description"],
        parameters=parameters,
        created_date=fields["created_date"],
        last_updated=fields["last_updated"],
        author=fields.get("author", ""),
        tags=fields.get("tags"),
    )


class AnalysisConfigurationManager:
    """Manages configuration-driven analysis parameters."""

    def __init__(self, config_directory: Path | None = None) -> None:
        """Initialize the configuration manager.

        Args:
            config_directory: Directory containing analysis configuration files

        """
        self.config_directory = (
            config_directory or Path(__file__).resolve().parents[2] / "configs"
        )
        self.config_directory.mkdir(exist_ok=True)
        self.configs: dict[str, AnalysisConfig] = {}
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Load default configurations
        self.load_default_configurations()

        self.logger.info(
            "AnalysisConfigurationManager initialized with directory: %s",
            self.config_directory,
        )

    def load_default_configurations(self) -> None:
        """Load default analysis configurations."""
        # Create default configurations if they don't exist
        default_configs = {
            "cost_driver_analysis": self._create_default_cost_driver_config(),
            "dsa_analysis": self._create_default_dsa_config(),
            "psa_analysis": self._create_default_psa_config(),
            "voi_analysis": self._create_default_voi_config(),
            "budget_impact_analysis": self._create_default_budget_impact_config(),
            "break_even_analysis": self._create_default_break_even_config(),
            "cost_effectiveness_analysis": (
                self._create_default_cost_effectiveness_config()
            ),
            "benchmarking_analysis": self._create_default_benchmarking_config(),
        }

        for config_name, config in default_configs.items():
            self.configs[config_name] = config
            # Save missing configurations.
            config_file = self.config_directory / f"{config_name}.yaml"
            if not config_file.exists():
                self.save_configuration(config_name, config_file)

    def _create_default_cost_driver_config(self) -> AnalysisConfig:
        """Create default configuration for cost driver analysis."""
        parameters = {
            "top_n_drivers": AnalysisParameter(
                name="top_n_drivers",
                value=10,
                description="Number of top cost drivers to display",
                data_type="int",
                default_value=10,
                min_value=1,
                max_value=100,
            ),
            "include_percentage": AnalysisParameter(
                name="include_percentage",
                value=True,
                description="Include percentage contribution in results",
                data_type="bool",
                default_value=True,
            ),
            "model_types": AnalysisParameter(
                name="model_types",
                value=["Panel", "WES", "WGS"],
                description="Types of models to analyze",
                data_type="list",
                default_value=["Panel", "WES", "WGS"],
            ),
        }

        return AnalysisConfig(
            analysis_type="cost_driver_analysis",
            version="1.0.0",
            description="Configuration for cost driver analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["cost_analysis", "drivers"],
        )

    def _create_default_dsa_config(self) -> AnalysisConfig:
        """Create default configuration for deterministic sensitivity analysis."""
        parameters = {
            "parameter_variations": AnalysisParameter(
                name="parameter_variations",
                value=[0.5, 0.75, 1.0, 1.25, 1.5],
                description="Variation factors for parameter sensitivity",
                data_type="list",
                default_value=[0.5, 0.75, 1.0, 1.25, 1.5],
            ),
            "include_tornado": AnalysisParameter(
                name="include_tornado",
                value=True,
                description="Include tornado diagram in results",
                data_type="bool",
                default_value=True,
            ),
            "top_sensitivity_parameters": AnalysisParameter(
                name="top_sensitivity_parameters",
                value=10,
                description="Number of top sensitivity parameters to display",
                data_type="int",
                default_value=10,
                min_value=1,
                max_value=50,
            ),
        }

        return AnalysisConfig(
            analysis_type="dsa_analysis",
            version="1.0.0",
            description="Configuration for deterministic sensitivity analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["sensitivity", "deterministic"],
        )

    def _create_default_psa_config(self) -> AnalysisConfig:
        """Create default configuration for probabilistic sensitivity analysis."""
        parameters = {
            "monte_carlo_iterations": AnalysisParameter(
                name="monte_carlo_iterations",
                value=1000,
                description="Number of Monte Carlo iterations",
                data_type="int",
                default_value=1000,
                min_value=100,
                max_value=100000,
            ),
            "confidence_intervals": AnalysisParameter(
                name="confidence_intervals",
                value=[2.5, 25, 50, 75, 97.5],
                description="Percentiles for confidence intervals",
                data_type="list",
                default_value=[2.5, 25, 50, 75, 97.5],
            ),
            "include_histogram": AnalysisParameter(
                name="include_histogram",
                value=True,
                description="Include histogram visualization",
                data_type="bool",
                default_value=True,
            ),
        }

        return AnalysisConfig(
            analysis_type="psa_analysis",
            version="1.0.0",
            description="Configuration for probabilistic sensitivity analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["sensitivity", "probabilistic", "monte_carlo"],
        )

    def _create_default_voi_config(self) -> AnalysisConfig:
        """Create default configuration for value of information analysis."""
        parameters = {
            "wtp_range": AnalysisParameter(
                name="wtp_range",
                value=[0, 100000],
                description="Willingness-to-pay range for VOI analysis",
                data_type="list",
                default_value=[0, 100000],
            ),
            "wtp_steps": AnalysisParameter(
                name="wtp_steps",
                value=100,
                description="Number of steps in WTP range",
                data_type="int",
                default_value=100,
                min_value=10,
                max_value=1000,
            ),
            "include_ceac": AnalysisParameter(
                name="include_ceac",
                value=True,
                description="Include cost-effectiveness acceptability curve",
                data_type="bool",
                default_value=True,
            ),
        }

        return AnalysisConfig(
            analysis_type="voi_analysis",
            version="1.0.0",
            description="Configuration for value of information analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["value_of_information", "evpi", "evppi"],
        )

    def _create_default_budget_impact_config(self) -> AnalysisConfig:
        """Create default configuration for budget impact analysis."""
        parameters = {
            "time_horizon": AnalysisParameter(
                name="time_horizon",
                value=5,
                description="Time horizon for budget impact analysis (years)",
                data_type="int",
                default_value=5,
                min_value=1,
                max_value=20,
            ),
            "discount_rate": AnalysisParameter(
                name="discount_rate",
                value=0.03,
                description="Discount rate for future costs",
                data_type="float",
                default_value=0.03,
                min_value=0.0,
                max_value=0.2,
            ),
            "volume_scenarios": AnalysisParameter(
                name="volume_scenarios",
                value=["low", "base", "high"],
                description="Volume scenarios to analyze",
                data_type="list",
                default_value=["low", "base", "high"],
            ),
        }

        return AnalysisConfig(
            analysis_type="budget_impact_analysis",
            version="1.0.0",
            description="Configuration for budget impact analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["budget", "impact", "forecasting"],
        )

    def _create_default_break_even_config(self) -> AnalysisConfig:
        """Create default configuration for break-even analysis."""
        parameters = {
            "price_range": AnalysisParameter(
                name="price_range",
                value=[0, 10000],
                description="Price range for break-even analysis",
                data_type="list",
                default_value=[0, 10000],
            ),
            "fixed_costs": AnalysisParameter(
                name="fixed_costs",
                value=500000,
                description="Fixed costs for break-even calculation",
                data_type="float",
                default_value=500000,
                min_value=0,
            ),
            "include_sensitivity": AnalysisParameter(
                name="include_sensitivity",
                value=True,
                description="Include sensitivity analysis in break-even results",
                data_type="bool",
                default_value=True,
            ),
        }

        return AnalysisConfig(
            analysis_type="break_even_analysis",
            version="1.0.0",
            description="Configuration for break-even analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["break_even", "cost_recovery"],
        )

    def _create_default_cost_effectiveness_config(self) -> AnalysisConfig:
        """Create default configuration for cost-effectiveness analysis."""
        parameters = {
            "effectiveness_measure": AnalysisParameter(
                name="effectiveness_measure",
                value="diagnostic_yield",
                description="Measure of effectiveness",
                data_type="str",
                default_value="diagnostic_yield",
                choices=["diagnostic_yield", "turnaround_time", "accuracy"],
            ),
            "include_technical_efficiency": AnalysisParameter(
                name="include_technical_efficiency",
                value=True,
                description="Include technical efficiency metrics",
                data_type="bool",
                default_value=True,
            ),
            "comparator_model": AnalysisParameter(
                name="comparator_model",
                value="WES",
                description="Comparator model for ICER calculation",
                data_type="str",
                default_value="WES",
                choices=["Panel", "WES", "WGS"],
            ),
        }

        return AnalysisConfig(
            analysis_type="cost_effectiveness_analysis",
            version="1.0.0",
            description="Configuration for cost-effectiveness analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["cost_effectiveness", "icer"],
        )

    def _create_default_benchmarking_config(self) -> AnalysisConfig:
        """Create default configuration for benchmarking analysis."""
        parameters = {
            "benchmark_sources": AnalysisParameter(
                name="benchmark_sources",
                value=["published_literature", "internal_data"],
                description="Sources of benchmark data",
                data_type="list",
                default_value=["published_literature", "internal_data"],
            ),
            "performance_metrics": AnalysisParameter(
                name="performance_metrics",
                value=["cost_per_test", "turnaround_time", "throughput"],
                description="Performance metrics to benchmark",
                data_type="list",
                default_value=["cost_per_test", "turnaround_time", "throughput"],
            ),
            "include_efficiency_metrics": AnalysisParameter(
                name="include_efficiency_metrics",
                value=True,
                description="Include efficiency metrics in benchmarking",
                data_type="bool",
                default_value=True,
            ),
        }

        return AnalysisConfig(
            analysis_type="benchmarking_analysis",
            version="1.0.0",
            description="Configuration for benchmarking analysis",
            parameters=parameters,
            created_date=datetime.now(UTC).isoformat(),
            last_updated=datetime.now(UTC).isoformat(),
            author="Microcosting Team",
            tags=["benchmarking", "comparison"],
        )

    def load_configuration(
        self,
        config_name: str,
        config_file: Path | None = None,
    ) -> AnalysisConfig:
        """Load an analysis configuration from a file.

        Args:
            config_name: Name of the configuration
            config_file: Path to the configuration file

        Returns:
            Loaded AnalysisConfig instance

        Raises:
            FileNotFoundError: If configuration file is not found
            ValueError: If there is an error parsing the configuration

        """
        if config_file is None:
            config_file = self.config_directory / f"{config_name}.yaml"

        self.logger.info("Loading configuration from %s", config_file)

        try:
            with Path(config_file).open() as f:
                config_data = yaml.safe_load(f)

            config = load_analysis_configuration(config_data)

            self.configs[config_name] = config
            self.logger.info("Loaded configuration: %s", config_name)

        except FileNotFoundError as exc:
            message = f"Configuration file not found: {config_file}"
            raise FileNotFoundError(message) from exc
        except Exception as e:
            message = f"Error loading configuration from {config_file}: {e}"
            raise ValueError(message) from e
        else:
            return config

    def save_configuration(
        self,
        config_name: str,
        config_file: Path | None = None,
    ) -> None:
        """Save an analysis configuration to a file.

        Args:
            config_name: Name of the configuration
            config_file: Path to the configuration file

        """
        if config_file is None:
            config_file = self.config_directory / f"{config_name}.yaml"

        config = self.configs.get(config_name)
        if config is None:
            message = f"Configuration {config_name} not found"
            raise ValueError(message)

        # Convert to serializable format
        config_dict: dict[str, object] = {
            "analysis_type": config.analysis_type,
            "version": config.version,
            "description": config.description,
            "created_date": config.created_date,
            "last_updated": config.last_updated,
            "author": config.author,
            "tags": config.tags,
            "parameters": {
                name: asdict(parameter) for name, parameter in config.parameters.items()
            },
        }

        # Save to file
        with Path(config_file).open("w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)

        self.logger.info("Saved configuration to %s", config_file)

    def get_configuration(self, config_name: str) -> AnalysisConfig | None:
        """Get a configuration by name.

        Args:
            config_name: Name of the configuration

        Returns:
            AnalysisConfig instance or None if not found

        """
        return self.configs.get(config_name)

    def list_configurations(self) -> list[str]:
        """List all available configurations.

        Returns:
            List of configuration names

        """
        return list(self.configs.keys())

    def get_parameter_value(
        self,
        config_name: str,
        parameter_name: str,
        default: object = None,
    ) -> object:
        """Get the value of a specific parameter from a configuration.

        Args:
            config_name: Name of the configuration
            parameter_name: Name of the parameter
            default: Default value if parameter not found

        Returns:
            Parameter value or default

        """
        config = self.get_configuration(config_name)
        if config is None:
            return default

        parameter = config.parameters.get(parameter_name)
        if parameter is None:
            return default

        return parameter.value

    def set_parameter_value(
        self,
        config_name: str,
        parameter_name: str,
        value: object,
    ) -> bool:
        """Set the value of a specific parameter in a configuration.

        Args:
            config_name: Name of the configuration
            parameter_name: Name of the parameter
            value: New value for the parameter

        Returns:
            True if successful, False if configuration or parameter not found

        """
        config = self.get_configuration(config_name)
        if config is None:
            return False

        parameter = config.parameters.get(parameter_name)
        if parameter is None:
            return False

        # Validate value if constraints are defined
        if (parameter.data_type == "int" and not isinstance(value, int)) or (
            parameter.data_type == "float" and not isinstance(value, (int, float))
        ):
            return False
        if (parameter.data_type == "bool" and not isinstance(value, bool)) or (
            parameter.choices is not None and value not in parameter.choices
        ):
            return False
        if (parameter.min_value is not None or parameter.max_value is not None) and (
            not isinstance(value, (int, float))
            or (parameter.min_value is not None and value < parameter.min_value)
            or (parameter.max_value is not None and value > parameter.max_value)
        ):
            return False

        parameter.value = value
        config.last_updated = datetime.now(UTC).isoformat()
        return True

    def validate_configuration(self, config_name: str) -> dict[str, list[str]]:
        """Validate a configuration for consistency and completeness.

        Args:
            config_name: Name of the configuration to validate

        Returns:
            Dictionary of validation issues (errors and warnings)

        """
        config = self.get_configuration(config_name)
        if config is None:
            return {
                "errors": [f"Configuration {config_name} not found"],
                "warnings": [],
            }

        issues: dict[str, list[str]] = {"errors": [], "warnings": []}

        # Validate required parameters
        for param_name, parameter in config.parameters.items():
            if parameter.required and parameter.value is None:
                issues["errors"].append(f"Required parameter {param_name} has no value")

        # Validate parameter constraints
        for param_name, parameter in config.parameters.items():
            value = parameter.value
            if value is None:
                continue
            if (
                parameter.min_value is not None or parameter.max_value is not None
            ) and not isinstance(value, (int, float)):
                issues["errors"].append(
                    f"Parameter {param_name} requires a numeric value",
                )
                continue
            if (
                isinstance(value, (int, float))
                and parameter.min_value is not None
                and value < parameter.min_value
            ):
                issues["errors"].append(
                    (
                        f"Parameter {param_name} value {parameter.value} "
                        f"is below minimum {parameter.min_value}"
                    ),
                )

            if (
                isinstance(value, (int, float))
                and parameter.max_value is not None
                and value > parameter.max_value
            ):
                issues["errors"].append(
                    (
                        f"Parameter {param_name} value {parameter.value} "
                        f"is above maximum {parameter.max_value}"
                    ),
                )

            if (parameter.choices is not None and parameter.value is not None) and (
                parameter.value not in parameter.choices
            ):
                issues["errors"].append(
                    (
                        f"Parameter {param_name} value {parameter.value} "
                        f"is not in allowed choices {parameter.choices}"
                    ),
                )

        return issues

    def generate_config_report(self, output_file: str | None = None) -> str:
        """Generate a comprehensive configuration report.

        Args:
            output_file: Optional file path to save the report

        Returns:
            Report as a string

        """
        try:
            report: list[str] = []
            report.append("# Analysis Configuration Report\n")
            report.append("## Executive Summary\n")
            report.append(
                "This report presents the available analysis configurations "
                "and their parameters.\n",
            )

            report.append("## Available Configurations\n")
            for config_name, config in self.configs.items():
                report.append(f"\n### {config_name}\n")
                report.append(f"- **Description**: {config.description}\n")
                report.append(f"- **Version**: {config.version}\n")
                report.append(f"- **Author**: {config.author}\n")
                report.append(f"- **Tags**: {', '.join(config.tags or ())}\n")
                report.append(f"- **Parameters**: {len(config.parameters)}\n")

                report.append("\n#### Parameters:\n")
                for param_name, parameter in config.parameters.items():
                    report.append(f"- **{param_name}** ({parameter.data_type})")
                    report.append(f"  - Description: {parameter.description}")
                    report.append(f"  - Value: {parameter.value}")
                    report.append(f"  - Default: {parameter.default_value}")
                    if parameter.min_value is not None:
                        report.append(f"  - Min: {parameter.min_value}")
                    if parameter.max_value is not None:
                        report.append(f"  - Max: {parameter.max_value}")
                    if parameter.choices is not None:
                        report.append(f"  - Choices: {parameter.choices}")
                    report.append("")

            report.append("## Key Features\n")
            report.append(
                "- Configuration-driven analysis parameters enable flexible and "
                "customizable analyses\n",
            )
            report.append(
                "- Default configurations provide sensible starting points "
                "for all analysis types\n",
            )
            report.append(
                "- Parameter validation ensures data integrity and consistency\n",
            )
            report.append("- Extensible design allows for custom configurations\n")
            report.append(
                "- YAML-based configuration files for easy editing and "
                "version control\n",
            )

            report_str = "\n".join(report)

            if output_file:
                with Path(output_file).open("w") as f:
                    f.write(report_str)

        except Exception:
            self.logger.exception("Error generating configuration report")
            raise
        else:
            return report_str


def main() -> None:
    """Run a demonstration of the analysis configuration system."""
    try:
        # Create configuration manager
        config_manager = AnalysisConfigurationManager()

        # Generate report
        report = config_manager.generate_config_report()
        logger.info("%s", report)

        # Save report to file
        output_file = (
            Path(__file__).resolve().parents[2]
            / "reports"
            / "analysis_configuration_report.md"
        )
        config_manager.generate_config_report(output_file=str(output_file))
        logger.info("%s", f"Report saved to {output_file}")

    except Exception:
        logger.exception("Error in analysis configuration system")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
