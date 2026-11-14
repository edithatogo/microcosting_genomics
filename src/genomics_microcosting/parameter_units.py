# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Explicit time-unit normalization for provenance-bound resource quantities."""

from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

lazy from .provenance_ledger import Parameter, SourceRecord


class TimeConversion(BaseModel):
    """Retain exact raw quantities and the evidence identifying their time unit."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    raw_value: Decimal = Field(ge=0, allow_inf_nan=False)
    source_unit: Literal["s", "min", "h"]
    target_unit: Literal["s", "min", "h"]
    source: SourceRecord
    unit_locator: str = Field(min_length=1, pattern=r".*\S.*")
    unit_basis: Literal["direct_label", "workbook_formula_inference"] = "direct_label"

    def exact_ratio(self) -> Fraction:
        """Retain the exact converted rational value before decimal rounding."""
        checked = TimeConversion.model_validate(self.model_dump())
        seconds = {"s": 1, "min": 60, "h": 3600}
        return (
            Fraction(checked.raw_value)
            * seconds[checked.source_unit]
            / seconds[checked.target_unit]
        )

    def derived_value(self) -> Decimal:
        """Return a decimal rendering with fifty significant digits for conversions.

        The exact rational remains available through exact_ratio; repeating
        decimals and large coefficients may round in this rendering.
        """
        checked = TimeConversion.model_validate(self.model_dump())
        if checked.source_unit == checked.target_unit:
            return checked.raw_value
        ratio = checked.exact_ratio()
        with localcontext() as context:
            context.prec = 50
            return Decimal(ratio.numerator) / Decimal(ratio.denominator)

    def is_rounded(self) -> bool:
        """Expose whether the decimal rendering loses exact rational precision."""
        return Fraction(self.derived_value()) != self.exact_ratio()


class TimeParameterTransform(BaseModel):
    """Bind a ledger value to its reproducible, source-bound time conversion."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter: Parameter
    conversion: TimeConversion
    rounding_policy: Literal["exact", "decimal-50"]

    @model_validator(mode="after")
    def consistent_values(self) -> Self:
        """Reject mismatched values, units, evidence or undeclared rounding."""
        parameter = self.parameter
        conversion = self.conversion
        if parameter.status != "derived":
            msg = "Converted time parameter must be derived"
            raise ValueError(msg)
        if (
            parameter.source_sha256 != conversion.source.sha256
            or parameter.source_locator != conversion.source.locator
            or parameter.unit != conversion.target_unit
        ):
            msg = "Time transformation source or target unit mismatch"
            raise ValueError(msg)
        if parameter.raw_value is None or parameter.derived_value is None:
            msg = "Time transformation requires raw and derived values"
            raise ValueError(msg)
        if (
            _finite_decimal(parameter.raw_value) != conversion.raw_value
            or _finite_decimal(parameter.derived_value) != conversion.derived_value()
        ):
            msg = "Time transformation parameter values mismatch"
            raise ValueError(msg)
        if self.rounding_policy == "exact" and conversion.is_rounded():
            msg = "Time transformation requires explicit rounding policy"
            raise ValueError(msg)
        return self


class CurrencyParameterTransform(BaseModel):
    """Bind an FX conversion to an independently qualified rate parameter.

    The denominator, price year and tax basis are unchanged declarations;
    evidence must separately establish their applicability.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    parameter: Parameter
    rate_parameter: Parameter
    source_currency: str = Field(pattern=r"^[A-Z]{3}$")
    target_currency: str = Field(pattern=r"^[A-Z]{3}$")
    denominator: str = Field(min_length=1, pattern=r"^\S(?:.*\S)?$")
    price_year: int = Field(ge=1900, le=9999)
    tax_basis: Literal["inclusive", "exclusive", "unknown"]
    rounding_policy: Literal["exact", "decimal-50"]

    @model_validator(mode="after")
    def consistent_values(self) -> Self:
        """Reject unsupported bases, rates, identities and arithmetic."""
        price = self.parameter
        rate = self.rate_parameter
        if (
            self.source_currency == self.target_currency
            or price.parameter_id == rate.parameter_id
            or price.status != "derived"
            or rate.status not in {"observed", "reported"}
            or price.unit != f"{self.target_currency}/{self.denominator}"
            or rate.unit != f"{self.target_currency}/{self.source_currency}"
            or price.raw_value is None
            or price.derived_value is None
            or rate.raw_value is None
            or rate.derived_value is None
        ):
            msg = "Currency transformation basis or rate is invalid"
            raise ValueError(msg)
        raw = _finite_decimal(price.raw_value)
        exchange = _finite_decimal(rate.raw_value)
        if raw < 0 or exchange <= 0 or exchange != _finite_decimal(rate.derived_value):
            msg = "Currency transformation requires a positive untransformed rate"
            raise ValueError(msg)
        exact = Fraction(raw) * Fraction(exchange)
        with localcontext() as context:
            context.prec = 50
            derived = Decimal(exact.numerator) / Decimal(exact.denominator)
        if _finite_decimal(price.derived_value) != derived:
            msg = "Currency transformation values mismatch"
            raise ValueError(msg)
        if self.rounding_policy == "exact" and Fraction(derived) != exact:
            msg = "Currency transformation requires explicit rounding policy"
            raise ValueError(msg)
        return self


def _finite_decimal(value: str) -> Decimal:
    """Turn malformed numerical claims into explicit validation failures."""
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        msg = "Time parameter value must be a finite decimal"
        raise ValueError(msg) from error
    if not result.is_finite():
        msg = "Time parameter value must be a finite decimal"
        raise ValueError(msg)
    return result
