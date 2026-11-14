# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Source-bound opt-in comparisons with explicit, caller-claimed qualification.

Validation cannot prove clinical equivalence, source interpretation or complete
cost accounting. Existing catalogue research leads remain non-costing.
"""

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
from typing import TYPE_CHECKING, Literal, Self
lazy from datetime import date

from openpyxl import load_workbook
from openpyxl.formula import Tokenizer
from pydantic import model_validator

from genomics_microcosting.alternative_research import ResearchCatalogue
from genomics_microcosting.parameter_provenance import (
    ComparisonResult,
    CostObservation,
    Digest,
    EvidenceComparison,
    NonEmpty,
    compare_costs,
)
from genomics_microcosting.parameter_units import (
    CurrencyParameterTransform,
    TimeParameterTransform,
)
from genomics_microcosting.provenance_ledger import (
    InputManifest,
    ParameterSet,
    QualificationLedger,
    SourceValidity,
    VersionDelta,
    require_resolved_parameters,
    verify_qualified_period,
)
from genomics_microcosting.t1_baseline_lineage import require_known_baseline_scope
from genomics_microcosting.uncertainty_provenance import UncertaintyLedger

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class ComparisonSources:
    """Bind workbook, source snapshots and declared baseline parameter set."""

    snapshots: dict[str, Path]
    workbook: Path
    baseline_parameters: ParameterSet | None


def compare_selected_scenario(
    catalogue_path: Path,
    scenario_id: str,
    comparison: EvidenceComparison | None,
    sources: ComparisonSources,
) -> ComparisonResult:
    """Bind a selected counterfactual to its catalogue and source observations."""
    catalogue = ResearchCatalogue.model_validate_json(catalogue_path.read_bytes())
    scenario = next(
        (s for s in catalogue.scenarios if s.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise KeyError(scenario_id)
    candidate = next(
        c for c in catalogue.candidates if c.candidate_id == scenario.candidate_id
    )
    if candidate.evidence_state != "qualified_for_comparison":
        message = "Candidate is not qualified for comparison"
        raise ValueError(message)
    if comparison is None:
        message = "A provenance comparison is required"
        raise ValueError(message)
    comparison = EvidenceComparison.model_validate(comparison.model_dump())
    if (
        scenario.kind != "changed_process_counterfactual"
        or comparison.scenario_id != scenario_id
        or comparison.baseline_workbook_sha256 != catalogue.workbook_sha256
    ):
        message = "Scenario or baseline identity mismatch"
        raise ValueError(message)
    baseline = comparison.baseline
    source = comparison.candidate.evidence
    if baseline.evidence.locator not in candidate.qualified_baseline_locations:
        message = "Baseline locator is outside the qualified scope"
        raise ValueError(message)
    selected_source = next(
        (s for s in catalogue.sources if s.source_id == source.source_id),
        None,
    )
    if (
        source.source_id not in candidate.source_ids
        or selected_source is None
        or source.snapshot_sha256 != selected_source.source_snapshot_sha256
        or selected_source.snapshot_url is None
        or source.source_url != selected_source.snapshot_url
    ):
        message = "Candidate source is not bound to the catalogue snapshot"
        raise ValueError(message)
    require_known_baseline_scope(
        catalogue.workbook_sha256,
        baseline.evidence.locator,
        candidate.required_baseline_parameter_ids,
    )
    if sources.baseline_parameters is None:
        message = "A scoped baseline parameter set is required"
        raise ValueError(message)
    require_resolved_parameters(
        sources.baseline_parameters,
        candidate.required_baseline_parameter_ids,
        catalogue.workbook_sha256,
    )
    result = compare_costs(comparison, sources.snapshots, sources.workbook)
    _verify_parameter_sources(
        sources.baseline_parameters,
        candidate.required_baseline_parameter_ids,
        sources,
    )
    verify_baseline_cell(baseline, sources.workbook)
    _verify_candidate_support(
        comparison.candidate,
        sources.snapshots[source.source_id],
    )
    return result


def _verify_parameter_sources(
    parameters: ParameterSet,
    required_ids: tuple[str, ...],
    sources: ComparisonSources,
) -> None:
    """Require actual source bytes for every declared baseline parameter."""
    needed = {
        item.source_sha256
        for item in parameters.parameters
        if item.parameter_id in required_ids
    }
    for path in (sources.workbook, *sources.snapshots.values()):
        if path.is_file():
            needed.discard(sha256(path.read_bytes()).hexdigest())
        if not needed:
            return
    message = "Required baseline parameter source snapshot missing or mismatched"
    raise ValueError(message)


def verify_baseline_cell(baseline: CostObservation, workbook: Path) -> None:
    """Check the cited cached baseline cell without changing the workbook."""
    match = re.fullmatch(r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)", baseline.evidence.locator)
    if match is None:
        message = "Baseline locator must identify a single workbook cell"
        raise ValueError(message)
    index = int(match.group(1)) - 1
    book = load_workbook(workbook, data_only=True, read_only=True)
    try:
        if index < 0 or index >= len(book.worksheets):
            message = "Baseline sheet does not exist"
            raise ValueError(message)
        value = book.worksheets[index][match.group(2)].value
    finally:
        book.close()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        message = "Baseline cached cell is not a numeric cost"
        raise TypeError(message)
    if Decimal(str(value)) != baseline.amount:
        message = "Baseline amount differs from the cached workbook cell"
        raise ValueError(message)


def _verify_candidate_support(candidate: CostObservation, snapshot: Path) -> None:
    """Check that source bytes contain the cited text and direct amount."""
    source = candidate.evidence
    try:
        text = snapshot.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        message = "Candidate source requires a verified UTF-8 text snapshot"
        raise ValueError(message) from exc
    support = source.exact_support
    numbers = re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])", support)
    try:
        values = {Decimal(n.replace(",", "")) for n in numbers}
    except InvalidOperation as exc:
        message = "Candidate source contains an invalid numeric value"
        raise ValueError(message) from exc
    if (
        support not in text
        or candidate.amount not in values
        or candidate.currency.casefold() not in support.casefold()
        or candidate.denominator.casefold() not in support.casefold()
    ):
        message = "Candidate source does not contain the exact supporting value"
        raise ValueError(message)


@dataclass(frozen=True)
class QualificationContext:
    """Select the exact ledger and evidence period used for comparison."""

    ledger: QualificationLedger
    validity: tuple[SourceValidity, ...]
    costing_date: date
    time_transforms: tuple[TimeParameterTransform, ...] = ()
    manifest: InputManifest | None = None
    currency_transforms: tuple[CurrencyParameterTransform, ...] = ()
    uncertainty: UncertaintyLedger | None = None


class QualifiedComparisonResult(ComparisonResult):
    """Retain the selected parameter, qualification and numerical model identities."""

    parameter_version_id: NonEmpty
    manifest_version_id: NonEmpty
    input_scope_sha256: Digest
    qualification_sha256: Digest
    catalogue_sha256: Digest
    costing_date: date
    parameter_set_sha256: Digest | None = None
    uncertainty_status: (
        Literal["not_assessed", "bounds_and_source_bytes_checked"] | None
    ) = None
    uncertainty_sha256: Digest | None = None
    model_version: Literal[
        "qualified-comparison-v2",
        "qualified-comparison-v3",
        "qualified-comparison-v4",
        "qualified-comparison-v5",
        "qualified-comparison-v6",
        "qualified-comparison-v7",
    ] = "qualified-comparison-v7"

    @model_validator(mode="after")
    def require_parameter_digest(self) -> Self:
        """Require exact parameter content identity for new results."""
        if (
            self.model_version
            in {
                "qualified-comparison-v4",
                "qualified-comparison-v5",
                "qualified-comparison-v6",
                "qualified-comparison-v7",
            }
            and self.parameter_set_sha256 is None
        ):
            message = "Version 4 result requires parameter content identity"
            raise ValueError(message)
        if self.model_version in {
            "qualified-comparison-v5",
            "qualified-comparison-v6",
            "qualified-comparison-v7",
        } and (
            self.uncertainty_status is None
            or (self.uncertainty_status == "bounds_and_source_bytes_checked")
            != (self.uncertainty_sha256 is not None)
        ):
            message = "Version 5 result requires consistent uncertainty status"
            raise ValueError(message)
        if self.model_version not in {
            "qualified-comparison-v5",
            "qualified-comparison-v6",
            "qualified-comparison-v7",
        } and (
            self.uncertainty_status is not None or self.uncertainty_sha256 is not None
        ):
            message = "Earlier result versions cannot claim uncertainty context"
            raise ValueError(message)
        return self


def parameter_set_digest(parameters: ParameterSet) -> str:
    """Hash a validated parameter set using canonical JSON encoding."""
    checked = ParameterSet.model_validate(parameters.model_dump())
    payload = json.dumps(
        checked.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode()).hexdigest()


def compare_qualified_scenario(
    catalogue_path: Path,
    scenario_id: str,
    comparison: EvidenceComparison,
    sources: ComparisonSources,
    qualification: QualificationContext,
) -> QualifiedComparisonResult:
    """Require dated ledger qualification before evaluating a selected scenario."""
    ledger = QualificationLedger.model_validate(qualification.ledger.model_dump())
    if sources.baseline_parameters != ledger.parameter_set:
        message = "Comparison parameter version differs from qualification ledger"
        raise ValueError(message)
    catalogue_bytes = catalogue_path.read_bytes()
    catalogue = ResearchCatalogue.model_validate_json(catalogue_bytes)
    scenario = next(
        (s for s in catalogue.scenarios if s.scenario_id == scenario_id),
        None,
    )
    if scenario is None:
        raise KeyError(scenario_id)
    candidate = next(
        c for c in catalogue.candidates if c.candidate_id == scenario.candidate_id
    )
    manifest, uncertainty = verify_qualified_inputs(
        qualification,
        sources,
        candidate.candidate_id,
        candidate.required_baseline_parameter_ids,
    )
    comparison = EvidenceComparison.model_validate(comparison.model_dump())
    periods = {item.source.source_id: item for item in qualification.validity}
    for observation in (comparison.baseline, comparison.candidate):
        evidence = observation.evidence
        period = periods.get(evidence.source_id)
        if period is None or (
            period.source.sha256 != evidence.snapshot_sha256
            or period.source.edition != evidence.edition
            or period.source.locator != evidence.locator
        ):
            message = "Observation source validity missing or mismatched"
            raise ValueError(message)
        period.require_applicable(qualification.costing_date)
    result = compare_selected_scenario(catalogue_path, scenario_id, comparison, sources)
    if catalogue_path.read_bytes() != catalogue_bytes:
        message = "Catalogue changed during qualified comparison"
        raise ValueError(message)
    context_payload = {
        "ledger": ledger.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "validity": [p.model_dump(mode="json") for p in qualification.validity],
        "transforms": [
            t.model_dump(mode="json") for t in qualification.time_transforms
        ],
        "currency_transforms": [
            t.model_dump(mode="json") for t in qualification.currency_transforms
        ],
        "uncertainty": uncertainty.model_dump(mode="json") if uncertainty else None,
        "costing_date": qualification.costing_date.isoformat(),
    }
    digest = sha256(
        json.dumps(context_payload, sort_keys=True, separators=(",", ":")).encode(),
    ).hexdigest()
    scope_payload = sorted(
        (
            item.input_id,
            item.resource_id,
            item.role,
            item.value_kind,
            item.formula_token_index,
        )
        for item in manifest.inputs
    )
    scope_digest = sha256(
        json.dumps(scope_payload, separators=(",", ":")).encode(),
    ).hexdigest()
    return QualifiedComparisonResult(
        **result.model_dump(),
        manifest_version_id=manifest.version_id,
        input_scope_sha256=scope_digest,
        parameter_version_id=ledger.parameter_set.version_id,
        parameter_set_sha256=parameter_set_digest(ledger.parameter_set),
        uncertainty_status=(
            "bounds_and_source_bytes_checked" if uncertainty else "not_assessed"
        ),
        uncertainty_sha256=(
            sha256(
                json.dumps(
                    uncertainty.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode(),
            ).hexdigest()
            if uncertainty
            else None
        ),
        qualification_sha256=digest,
        catalogue_sha256=sha256(catalogue_bytes).hexdigest(),
        costing_date=qualification.costing_date,
    )


def verify_qualified_inputs(
    qualification: QualificationContext,
    sources: ComparisonSources,
    candidate_id: str,
    baseline_ids: tuple[str, ...],
) -> tuple[InputManifest, UncertaintyLedger | None]:
    """Verify declared input sources and transforms without calculating a total."""
    ledger = QualificationLedger.model_validate(qualification.ledger.model_dump())
    if sources.baseline_parameters != ledger.parameter_set:
        message = "Comparison parameter version differs from qualification ledger"
        raise ValueError(message)
    manifest = _bound_input_manifest(
        qualification,
        candidate_id,
        baseline_ids,
    )
    numeric_ids = tuple(
        item.input_id for item in manifest.inputs if item.value_kind != "workbook_text"
    )
    scalar_ids = tuple(
        item.input_id for item in manifest.inputs if item.value_kind == "numeric"
    )
    text_ids = tuple(
        item.input_id for item in manifest.inputs if item.value_kind == "workbook_text"
    )
    verify_qualified_period(
        ledger,
        sources.snapshots,
        qualification.validity,
        required_ids=manifest.required_ids,
        costing_date=qualification.costing_date,
    )
    _verify_raw_workbook_parameters(
        ledger.parameter_set,
        scalar_ids,
        sources.workbook,
    )
    _verify_workbook_text_parameters(ledger, text_ids, sources.workbook)
    _verify_workbook_formula_numbers(ledger, manifest, sources.workbook)
    verify_external_parameter_values(ledger, scalar_ids, sources.snapshots)
    _verify_parameter_transformations(
        ledger.parameter_set,
        numeric_ids,
        qualification.time_transforms,
        qualification.currency_transforms,
    )
    verify_time_unit_sources(ledger, qualification.time_transforms, sources.snapshots)
    uncertainty = _checked_uncertainty(
        qualification,
        ledger.parameter_set,
        numeric_ids,
        sources.snapshots,
    )
    return manifest, uncertainty


def _checked_uncertainty(
    context: QualificationContext,
    parameters: ParameterSet,
    required_ids: tuple[str, ...],
    snapshots: dict[str, Path],
) -> UncertaintyLedger | None:
    """Check declared uncertainty without asserting statistical adequacy."""
    if context.uncertainty is None:
        return None
    uncertainty = UncertaintyLedger.model_validate(context.uncertainty.model_dump())
    if uncertainty.parameter_set != parameters:
        message = "Uncertainty parameter version differs from selected ledger"
        raise ValueError(message)
    uncertainty.verify_required(required_ids, snapshots)
    periods = {item.source.source_id: item for item in context.validity}
    for record in uncertainty.records:
        if record.measure_id not in required_ids:
            continue
        for source in (
            record.source,
            record.interpretation_evidence.source,
            record.distribution.source,
            record.dependence.source,
        ):
            if source is None:
                message = "Uncertainty source missing"
                raise ValueError(message)
            period = periods.get(source.source_id)
            if period is None or period.source != source:
                message = "Uncertainty source validity missing or mismatched"
                raise ValueError(message)
            period.require_applicable(context.costing_date)
    return uncertainty


def verify_external_parameter_values(
    ledger: QualificationLedger,
    required_ids: tuple[str, ...],
    snapshots: dict[str, Path],
) -> None:
    """Check external numeric claims against exact retained UTF-8 source text.

    Only one-based ``line N`` locators in UTF-8 text are supported. Text
    matching does not establish semantic interpretation, units or rights.
    Other locators and binary evidence require a qualified extractor.
    """
    ledger = QualificationLedger.model_validate(ledger.model_dump())
    ledger.require_qualified(required_ids)
    for record in ledger.qualifications:
        parameter = record.parameter
        if (
            parameter.parameter_id not in required_ids
            or parameter.source_sha256 == ledger.parameter_set.workbook_sha256
        ):
            continue
        path = snapshots.get(record.source.source_id)
        if path is None or not path.is_file():
            message = "External parameter source support is missing"
            raise ValueError(message)
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != record.source.sha256:
            message = "External parameter source support hash mismatch"
            raise ValueError(message)
        try:
            text = payload.decode("utf-8")
            raw = Decimal(parameter.raw_value or "NaN")
        except (UnicodeDecodeError, InvalidOperation) as error:
            message = "External parameter source support is unsupported"
            raise ValueError(message) from error
        match = re.fullmatch(r"line ([1-9][0-9]*)", record.source.locator)
        lines = text.splitlines()
        if (
            match is None
            or parameter.source_locator != record.source.locator
            or int(match.group(1)) > len(lines)
        ):
            message = "External parameter source locator is unsupported or mismatched"
            raise ValueError(message)
        source_line = lines[int(match.group(1)) - 1]
        numbers = re.findall(
            r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])",
            record.exact_support,
        )
        values = {Decimal(number.replace(",", "")) for number in numbers}
        if (
            not raw.is_finite()
            or record.exact_support not in source_line
            or raw not in values
        ):
            message = "External parameter source support does not match raw value"
            raise ValueError(message)


def _verify_raw_workbook_parameters(
    parameters: ParameterSet,
    required_ids: tuple[str, ...],
    workbook: Path,
) -> None:
    """Bind adopted workbook parameters to their exact cited cached scalar."""
    book = load_workbook(workbook, data_only=True, read_only=True)
    try:
        for parameter in parameters.parameters:
            if (
                parameter.parameter_id not in required_ids
                or parameter.source_sha256 != parameters.workbook_sha256
            ):
                continue
            match = re.fullmatch(
                r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)",
                parameter.source_locator,
            )
            if match is None or not 1 <= int(match.group(1)) <= len(book.worksheets):
                message = "Required parameter workbook locator is invalid"
                raise ValueError(message)
            value = book.worksheets[int(match.group(1)) - 1][match.group(2)].value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                message = "Required parameter cached value is not numeric"
                raise TypeError(message)
            try:
                raw = Decimal(parameter.raw_value or "NaN")
            except InvalidOperation as error:
                message = "Required parameter raw value is not numeric"
                raise ValueError(message) from error
            if not raw.is_finite() or raw != Decimal(str(value)):
                message = "Required parameter raw value differs from workbook cell"
                raise ValueError(message)
    finally:
        book.close()


def _verify_workbook_formula_numbers(
    ledger: QualificationLedger,
    manifest: InputManifest,
    workbook: Path,
) -> None:
    """Verify a numeric token at its exact source-formula position."""
    requirements = {
        item.input_id: item
        for item in manifest.inputs
        if item.value_kind == "workbook_formula_number"
    }
    if not requirements:
        return
    checked = QualificationLedger.model_validate(ledger.model_dump())
    book = load_workbook(workbook, data_only=False, read_only=True)
    try:
        for record in checked.qualifications:
            parameter = record.parameter
            item = requirements.get(parameter.parameter_id)
            if item is None:
                continue
            match = re.fullmatch(
                r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)",
                parameter.source_locator,
            )
            if (
                parameter.source_sha256 != checked.parameter_set.workbook_sha256
                or match is None
                or item.formula_token_index is None
                or not 1 <= int(match.group(1)) <= len(book.worksheets)
            ):
                message = "Workbook formula-number source or locator is unsupported"
                raise ValueError(message)
            formula = book.worksheets[int(match.group(1)) - 1][match.group(2)].value
            if not isinstance(formula, str) or not formula.startswith("="):
                message = "Workbook formula-number source is not a formula"
                raise ValueError(message)
            tokens = Tokenizer(formula).items
            index = item.formula_token_index - 1
            if index >= len(tokens):
                message = "Workbook formula-number token position is unsupported"
                raise ValueError(message)
            token = tokens[index]
            if (
                token.type != "OPERAND"
                or token.subtype != "NUMBER"
                or parameter.raw_value != token.value
                or record.exact_support != formula
            ):
                message = "Workbook formula-number evidence differs from source"
                raise ValueError(message)
    finally:
        book.close()


def _verify_workbook_text_parameters(
    ledger: QualificationLedger,
    required_ids: tuple[str, ...],
    workbook: Path,
) -> None:
    """Verify declared text evidence as exact workbook content, never a number."""
    if not required_ids:
        return
    checked = QualificationLedger.model_validate(ledger.model_dump())
    book = load_workbook(workbook, data_only=True, read_only=True)
    try:
        for record in checked.qualifications:
            parameter = record.parameter
            if parameter.parameter_id not in required_ids:
                continue
            match = re.fullmatch(
                r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)",
                parameter.source_locator,
            )
            if (
                parameter.source_sha256 != checked.parameter_set.workbook_sha256
                or parameter.status not in {"observed", "reported"}
                or match is None
                or not 1 <= int(match.group(1)) <= len(book.worksheets)
            ):
                message = "Workbook text evidence source or locator is unsupported"
                raise ValueError(message)
            value = book.worksheets[int(match.group(1)) - 1][match.group(2)].value
            if (
                not isinstance(value, str)
                or parameter.raw_value != value
                or parameter.derived_value != value
                or record.exact_support != value
            ):
                message = "Workbook text evidence differs from the cited cell"
                raise ValueError(message)
    finally:
        book.close()


def _verify_parameter_transformations(
    parameters: ParameterSet,
    required_ids: tuple[str, ...],
    transforms: tuple[TimeParameterTransform, ...],
    currency_transforms: tuple[CurrencyParameterTransform, ...],
) -> None:
    """Require reproducible supported transforms for changed numeric values."""
    checked = tuple(
        TimeParameterTransform.model_validate(t.model_dump()) for t in transforms
    )
    currency = tuple(
        CurrencyParameterTransform.model_validate(t.model_dump())
        for t in currency_transforms
    )
    all_transforms = (*checked, *currency)
    by_id = {t.parameter.parameter_id: t for t in all_transforms}
    if len(by_id) != len(all_transforms):
        message = "Duplicate parameter transformation"
        raise ValueError(message)
    _verify_transform_bindings(parameters, required_ids, all_transforms, currency)
    for parameter in parameters.parameters:
        if parameter.parameter_id not in required_ids:
            continue
        try:
            raw = Decimal(parameter.raw_value or "NaN")
            derived = Decimal(parameter.derived_value or "NaN")
        except InvalidOperation as error:
            message = "Numerical parameter transformation is unsupported"
            raise ValueError(message) from error
        if raw.is_finite() and derived.is_finite() and raw == derived:
            continue
        transform = by_id.get(parameter.parameter_id)
        if transform is None or transform.parameter != parameter:
            message = "Required derived parameter transformation missing or mismatched"
            raise ValueError(message)


def verify_time_unit_sources(
    ledger: QualificationLedger,
    transforms: tuple[TimeParameterTransform, ...],
    snapshots: dict[str, Path],
) -> None:
    """Verify direct unit tokens or an explicitly selected formula inference."""
    ledger = QualificationLedger.model_validate(ledger.model_dump())
    qualifications = {q.parameter.parameter_id: q for q in ledger.qualifications}
    for item in transforms:
        transform = TimeParameterTransform.model_validate(item.model_dump())
        conversion = transform.conversion
        record = qualifications.get(transform.parameter.parameter_id)
        if record is None or record.source != conversion.source:
            message = "Time unit source differs from parameter qualification"
            raise ValueError(message)
        path = snapshots.get(conversion.source.source_id)
        if (
            path is None
            or not path.is_file()
            or (sha256(path.read_bytes()).hexdigest() != conversion.source.sha256)
        ):
            message = "Time unit source snapshot missing or mismatched"
            raise ValueError(message)
        if conversion.unit_basis == "workbook_formula_inference":
            _verify_workbook_time_inference(transform, ledger, path)
            continue
        _verify_direct_time_unit(transform, ledger, path)


def _verify_direct_time_unit(
    transform: TimeParameterTransform,
    ledger: QualificationLedger,
    path: Path,
) -> None:
    """Check the supported direct unit token at its exact locator."""
    conversion = transform.conversion
    locator = conversion.unit_locator
    tokens = {
        "s": {"s", "sec", "second", "seconds"},
        "min": {"min", "minute", "minutes"},
        "h": {"h", "hr", "hour", "hours"},
    }
    match = re.fullmatch(r"WB(\d{2}):([A-Z]{1,3}[1-9]\d*)", locator)
    line = re.fullmatch(r"line ([1-9][0-9]*)", locator)
    value: object = None
    if (
        match is not None
        and conversion.source.sha256 == ledger.parameter_set.workbook_sha256
    ):
        book = load_workbook(path, data_only=True, read_only=True)
        try:
            index = int(match.group(1)) - 1
            if 0 <= index < len(book.worksheets):
                value = book.worksheets[index][match.group(2)].value
        finally:
            book.close()
    elif line is not None:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as error:
            message = "Time unit source is not UTF-8 text"
            raise ValueError(message) from error
        index = int(line.group(1)) - 1
        if index < len(lines):
            value = lines[index]
    if (
        not isinstance(value, str)
        or value.strip().casefold() not in tokens[conversion.source_unit]
    ):
        message = "Time unit source locator or value is unsupported or mismatched"
        raise ValueError(message)


def _verify_workbook_time_inference(
    transform: TimeParameterTransform,
    ledger: QualificationLedger,
    workbook: Path,
) -> None:
    """Check one narrow historical formula pattern, without proving measurement."""
    conversion = transform.conversion
    match = re.fullmatch(
        r"WB(\d{2}):AA([1-9]\d*):AC\2; WB(\d{2}):AB1 hourly salary header",
        conversion.unit_locator,
    )
    if (
        match is None
        or conversion.source_unit != "min"
        or conversion.source.sha256 != ledger.parameter_set.workbook_sha256
        or transform.parameter.source_locator != f"WB{match.group(1)}:G{match.group(2)}"
    ):
        message = "Unsupported workbook time-unit inference"
        raise ValueError(message)
    book = load_workbook(workbook, data_only=False, read_only=False)
    try:
        timing_index, row, rate_index = (int(part) for part in match.groups())
        if not (1 <= timing_index <= len(book.worksheets)) or not (
            1 <= rate_index <= len(book.worksheets)
        ):
            message = "Unsupported workbook time-unit inference"
            raise ValueError(message)
        timing, rates = (
            book.worksheets[timing_index - 1],
            book.worksheets[rate_index - 1],
        )
        if rates["AB1"].value != "Base Salary + Costs (hourly)" or (
            "AB1:AD1" not in {str(item) for item in rates.merged_cells.ranges}
        ):
            message = "Workbook hourly rate header differs"
            raise ValueError(message)
        sheet_name = rates.title.replace("'", "''")
        for cost, rate, source in (
            ("AA", "K", "AB"),
            ("AB", "L", "AC"),
            ("AC", "M", "AD"),
        ):
            if timing[f"{cost}{row}"].value != f"=$G{row}/60*{rate}{row}" or (
                timing[f"{rate}{row}"].value != f"='{sheet_name}'!{source}$4"
            ):
                message = "Workbook time inference formula or rate link differs"
                raise ValueError(message)
    finally:
        book.close()


def _verify_transform_bindings(
    parameters: ParameterSet,
    required_ids: tuple[str, ...],
    transforms: tuple[TimeParameterTransform | CurrencyParameterTransform, ...],
    currency: tuple[CurrencyParameterTransform, ...],
) -> None:
    """Bind every transform and its rate to the complete required input scope."""
    by_parameter = {p.parameter_id: p for p in parameters.parameters}
    for transform in transforms:
        parameter = transform.parameter
        if (
            parameter.parameter_id not in required_ids
            or by_parameter.get(parameter.parameter_id) != parameter
        ):
            message = "Transformation must match a required ledger parameter"
            raise ValueError(message)
    for transform in currency:
        if transform.tax_basis == "unknown":
            message = "Currency transformation tax basis is unresolved"
            raise ValueError(message)
        rate = transform.rate_parameter
        if (
            rate.parameter_id not in required_ids
            or by_parameter.get(rate.parameter_id) != rate
        ):
            message = (
                "Currency rate must be a required parameter in the selected ledger"
            )
            raise ValueError(message)


@dataclass(frozen=True)
class VersionResultDelta:
    """Retain both results alongside their selected parameter transition."""

    before: QualifiedComparisonResult
    after: QualifiedComparisonResult
    parameters: VersionDelta
    result_delta: Decimal


def reconcile_version_results(
    before: QualifiedComparisonResult,
    after: QualifiedComparisonResult,
    transition: VersionDelta,
) -> VersionResultDelta:
    """Compare compatible records without claiming causal attribution."""
    before = QualifiedComparisonResult.model_validate(before.model_dump())
    after = QualifiedComparisonResult.model_validate(after.model_dump())
    transition = VersionDelta.model_validate(transition.model_dump())
    if (
        before.parameter_version_id != transition.baseline.version_id
        or after.parameter_version_id != transition.successor.version_id
        or before.baseline_workbook_sha256 != transition.baseline.workbook_sha256
        or after.baseline_workbook_sha256 != transition.successor.workbook_sha256
    ):
        message = "Result identities do not match parameter transition"
        raise ValueError(message)
    compatible_versions = {
        "qualified-comparison-v4",
        "qualified-comparison-v5",
        "qualified-comparison-v6",
        "qualified-comparison-v7",
    }
    if (
        before.model_version not in compatible_versions
        or after.model_version not in compatible_versions
        or before.parameter_set_sha256 != parameter_set_digest(transition.baseline)
        or after.parameter_set_sha256 != parameter_set_digest(transition.successor)
    ):
        message = "Result parameter content identity is missing or mismatched"
        raise ValueError(message)
    if any(
        result.model_version
        in {
            "qualified-comparison-v5",
            "qualified-comparison-v6",
            "qualified-comparison-v7",
        }
        and result.uncertainty_status != "not_assessed"
        for result in (before, after)
    ):
        message = "Reconciliation of declared uncertainty is unsupported"
        raise ValueError(message)
    before_basis = (
        before.scenario_id,
        before.model_version,
        before.catalogue_sha256,
        before.input_scope_sha256,
        before.costing_date,
        before.baseline,
    )
    after_basis = (
        after.scenario_id,
        after.model_version,
        after.catalogue_sha256,
        after.input_scope_sha256,
        after.costing_date,
        after.baseline,
    )
    attributes = ("currency", "price_year", "denominator", "tax_basis")
    if before_basis != after_basis or any(
        getattr(before.candidate, name) != getattr(after.candidate, name)
        for name in attributes
    ):
        message = "Version results have incompatible costing bases"
        raise ValueError(message)
    with localcontext() as context:
        context.prec = 50
        difference = after.delta - before.delta
    return VersionResultDelta(before, after, transition, difference)


def _bound_input_manifest(
    context: QualificationContext,
    candidate_id: str,
    baseline_ids: tuple[str, ...],
) -> InputManifest:
    """Require complete declared manifest disposition and exact ledger binding."""
    if context.manifest is None:
        message = "Required input manifest is missing"
        raise ValueError(message)
    manifest = InputManifest.model_validate(context.manifest.model_dump())
    manifest.require_ready()
    records = {q.parameter.parameter_id: q for q in context.ledger.qualifications}
    numeric_ids = {
        item.input_id for item in manifest.inputs if item.value_kind != "workbook_text"
    }
    if (
        manifest.candidate_id != candidate_id
        or manifest.workbook_sha256 != context.ledger.parameter_set.workbook_sha256
        or not numeric_ids
        or not set(baseline_ids) <= numeric_ids
        or set(manifest.required_ids) != records.keys()
    ):
        message = "Input manifest identity or ledger coverage mismatch"
        raise ValueError(message)
    if any(
        item.blockers or item.qualification != records[item.input_id]
        for item in manifest.inputs
    ):
        message = "Input manifest contains blocked or mismatched qualifications"
        raise ValueError(message)
    return manifest
