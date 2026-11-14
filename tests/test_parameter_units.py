# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Check explicit unit normalization and reject unsupported dimensions."""

from decimal import Decimal
from fractions import Fraction

import pytest

from genomics_microcosting.parameter_units import (
    CurrencyParameterTransform,
    TimeConversion,
    TimeParameterTransform,
)
from genomics_microcosting.provenance_ledger import Parameter, SourceRecord
from tests import checks


def test_currency_transform_requires_qualified_rate_and_stable_cost_basis() -> None:
    """A conversion carries its rate identity and cannot silently change basis."""
    price = Parameter(
        parameter_id="price",
        raw_value="100",
        derived_value="150",
        unit="AUD/sample",
        source_sha256="a" * 64,
        source_locator="line 1",
        transformation="USD to AUD",
        uncertainty="synthetic",
        status="derived",
    )
    rate = Parameter(
        parameter_id="fx",
        raw_value="1.5",
        derived_value="1.5",
        unit="AUD/USD",
        source_sha256="b" * 64,
        source_locator="line 1",
        transformation="identity",
        uncertainty="synthetic",
        status="observed",
    )
    fields = {
        "parameter": price,
        "rate_parameter": rate,
        "source_currency": "USD",
        "target_currency": "AUD",
        "denominator": "sample",
        "price_year": 2023,
        "tax_basis": "exclusive",
        "rounding_policy": "exact",
    }
    transform = CurrencyParameterTransform.model_validate(fields)
    checks.require_equal(transform.parameter.derived_value, "150")
    for update in (
        {"rate_parameter": rate.model_copy(update={"unit": "USD/AUD"})},
        {"rate_parameter": rate.model_copy(update={"derived_value": "0"})},
        {"parameter": price.model_copy(update={"derived_value": "149"})},
        {"denominator": "test"},
        {"target_currency": "USD"},
    ):
        with pytest.raises(ValueError, match="Currency transformation"):
            CurrencyParameterTransform.model_validate(fields | update)


def test_time_conversion_preserves_quantity_and_source() -> None:
    """Minute quantities normalize to hours without altering the raw record."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="synthetic",
        locator="A1",
        limitations="synthetic unit evidence",
    )
    conversion = TimeConversion(
        raw_value=Decimal(90),
        source_unit="min",
        target_unit="h",
        source=source,
        unit_locator="A2 time (minutes)",
    )
    checks.require_equal(conversion.derived_value(), Decimal("1.5"))
    checks.require_equal(conversion.raw_value, Decimal(90))
    reverse = TimeConversion.model_validate(
        conversion.model_dump()
        | {
            "raw_value": conversion.derived_value(),
            "source_unit": "h",
            "target_unit": "min",
        },
    )
    checks.require_equal(reverse.derived_value(), conversion.raw_value)
    with pytest.raises(ValueError, match="Input should be"):
        TimeConversion.model_validate(conversion.model_dump() | {"target_unit": "AUD"})
    with pytest.raises(ValueError, match="finite"):
        TimeConversion.model_validate(conversion.model_dump() | {"raw_value": "NaN"})
    invalid = conversion.model_copy(update={"raw_value": Decimal(-1)})
    with pytest.raises(ValueError, match="greater than or equal"):
        invalid.derived_value()


def test_repeating_conversions_expose_rounding_and_preserve_identity() -> None:
    """Decimal rendering must not masquerade as exact dimensional conversion."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="v1",
        locator="A1",
        limitations="synthetic",
    )
    conversion = TimeConversion(
        raw_value=Decimal(1),
        source_unit="s",
        target_unit="h",
        source=source,
        unit_locator="seconds",
    )
    checks.require_equal(conversion.exact_ratio(), Fraction(1, 3600))
    checks.require_equal(conversion.is_rounded(), expected=True)
    large = Decimal(123456789012345678901234567890123456789012345678901234567890)
    identity = TimeConversion.model_validate(
        conversion.model_dump() | {"raw_value": large, "target_unit": "s"},
    )
    checks.require_equal(identity.derived_value(), large)
    checks.require_equal(identity.is_rounded(), expected=False)


def test_time_parameter_transform_rejects_inconsistent_ledger_values() -> None:
    """A transformation label cannot substitute for reproducible value linkage."""
    source = SourceRecord(
        source_id="s",
        sha256="a" * 64,
        edition="v1",
        locator="A1",
        limitations="synthetic",
    )
    conversion = TimeConversion(
        raw_value=Decimal(90),
        source_unit="min",
        target_unit="h",
        source=source,
        unit_locator="A2",
    )
    parameter = Parameter(
        parameter_id="time",
        raw_value="90",
        derived_value="1.5",
        unit="h",
        source_sha256="a" * 64,
        source_locator="A1",
        transformation="minutes to hours",
        uncertainty="synthetic",
        status="derived",
    )
    transform = TimeParameterTransform(
        parameter=parameter,
        conversion=conversion,
        rounding_policy="exact",
    )
    checks.require_equal(transform.parameter.derived_value, "1.5")
    for update, message in [
        ({"raw_value": "not numeric"}, "finite decimal"),
        ({"derived_value": "NaN"}, "finite decimal"),
        ({"derived_value": "Infinity"}, "finite decimal"),
        ({"derived_value": "2"}, "values mismatch"),
        ({"unit": "min"}, "unit mismatch"),
        ({"source_sha256": "b" * 64}, "source or target"),
    ]:
        with pytest.raises(ValueError, match=message):
            TimeParameterTransform(
                parameter=parameter.model_copy(update=update),
                conversion=conversion,
                rounding_policy="exact",
            )
