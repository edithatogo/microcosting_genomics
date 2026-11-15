# Dapane manual DNA extraction adapter

This optional provider path maps the two labour steps of the preserved manual
DNA extraction stage to the common Dapane Rust valuation and allocation kernel.
The existing CalculationEngine and other costing functions retain their current
behaviour. Installing this provider does not install Dapane or change engines
implicitly.

The coordinating implementation record is
[Dapane's Python/two-consumer track](https://github.com/edithatogo/dapane/tree/main/conductor/tracks/python_two_consumers_20261108).
This provider owns the source mapping, batch/attempt interpretation and old entry
points. Dapane owns numerical methods and installed cross-provider qualification.

## Selected source and explicit assumptions

The preserved v15 workbook has SHA-256
2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4.
The adapter selects only the Labour - Usage - VCGS sheet:

| Source cells | Meaning in this bounded mapping |
| --- | --- |
| D22, E22, G22 | Labwork batch minutes, nominal six specimens, per-specimen division |
| D23, E23, G23 | Administration batch minutes, nominal six specimens, per-specimen division |
| L22, L23 | The historical midpoint loaded hourly quotation |
| AB22, AB23, AB24 | Historical calculated line costs and their subtotal |

The new path retains the batch effort when fewer than six specimens are named.
It allocates the whole incurred batch pool over the actual named specimens.
Unused physical slots do not invent utilization, resource consumption or a
separate capital-capacity denominator. Equipment, consumables and other assay
stages are outside this adapter.

The historical LT role and a selected workforce classification are not assumed
equivalent. Every invocation requires role_mapping_basis, retained verbatim in
the resulting source provenance. The demonstrator selects a published
Queensland Health hourly reference; its base-only inclusion excludes all other
labour components. This is a declared comparison scenario, not a payroll or
classification-eligibility determination.

## Source release and interpreter boundary

The provider still requires **Python 3.15.1** and its existing locked
dependencies. Workforce has its own independent runtime. Exchange a reviewed
workforce-dapane-quotes/1 JSON artifact; do not import workforce into this
environment or relax either provider's Python requirement.

The artifact includes its original accepted quotation release, source identities,
explicit hour-to-minute denominator binding, and exact component inclusion.
Its canonical UTF-8 JSON identity uses sorted keys, compact separators and
unescaped Unicode. The release_sha256 covers the complete original release snapshot;
artifact_sha256 covers the envelope without that one digest field. Supply the
expected artifact digest separately from the JSON input.

The loader rejects duplicate keys, binary/nonfinite JSON numbers, malformed or
unknown envelope versions, changed digests, unsupported source kinds, invented
component inclusions, source/projection disagreement, unsupported dates and
quotes unavailable at the selected knowledge cutoff. It accepts only the
published-wage-reference and explicitly synthetic source profiles. The profile's
verified_through and quotation end dates are exclusive.

Selecting one already loaded quotation preserves its declared component exactly.
The adapter provides no automatic salary/on-cost additions. Review inclusion
before selecting a different release.

## Explicit batch attempts

ExtractionBatch contains a batch identity, a tuple of one to six unique
specimen identities, an outcome (completed or failed), and optional repeat_of.
Both outcomes retain the same explicitly incurred labour uses.

A repeat must point to an earlier failed batch with the identical specimen set.
One failed batch can have only one direct successor. Cycles, forward references,
retrying a completed batch, changing the cohort during retry, and independently
reusing a specimen identity fail before pricing. Each physical attempt retains a
separate source ledger and rounded allocation pool.

These restrictions define this first adapter. It does not infer failure
probabilities, partial-step repeats, actual staff use from elapsed duration,
clinical outcome, reportability or completeness of the full assay.

The repository's existing probabilistic sensitivity analysis (PSA) and value of
information (VOI) demonstrations remain separate examples. This adapter does not
route them through Dapane, and the installed qualification for this selected
manual-extraction stage makes no acceptance claim about those demonstrations.

## Installed use

Install separately built, qualified provider and Dapane wheels into the
Python 3.15.1 environment. Run outside both repositories with isolated imports.
The Dapane coordinator records the exact wheel/platform evidence.

~~~python
from pathlib import Path

from genomics_microcosting.dapane_adapter import (
    ExtractionBatch,
    evaluate_manual_dna_extraction,
    manual_dna_extraction_request,
)

raw_release = Path("reviewed-workforce-artifact.json").read_bytes()
expected_digest = "the independently selected 64-character artifact SHA-256"
options = dict(
    release_digest=expected_digest,
    quote_id="qld-hp3p1-minute-20260901",
    batches=(ExtractionBatch("batch-001", ("synthetic-a", "synthetic-b")),),
    service_date="2026-11-15",
    knowledge_cutoff="2026-11-15",
    role_mapping_basis="Declared comparison: historical LT stage to HP3.1 base reference",
    run_id="manual-extraction-comparison",
)
request = manual_dna_extraction_request(raw_release, **options)
report = evaluate_manual_dna_extraction(raw_release, **options)
~~~

The request constructor performs structural/source mapping only. The
evaluation function calls dapane.evaluate; it propagates structured native
errors and fails if no native wheel is installed. The request can also be sent
unchanged to Dapane's CLI for independent surface parity.

The current published-reference artifact is bounded to its observed source
horizon. Do not extend its dates or substitute a new amount without preparing and
reviewing a new provider release.

## Historical comparison and rollback

The dapane_workbook module's inspect_manual_extraction_workbook(path)
checks the entire workbook hash before returning selected cell formula/cache
observations. It expands Excel shared-formula references through the existing
read-only reader and preserves raw XML cached numeric strings. It never
recalculates or changes source bytes.

The historical_manual_extraction_request(path) function emits the selected
historical per-specimen exposures, including the exact nonterminating
administration exposure, for Rust replay. The replay date/year label the workbook
snapshot; they do not newly establish the historic economic price basis or
employment period. The historical quotation is retained as an opaque loaded
component with unresolved decomposition.

The compare_manual_extraction_workbook(path, current_report) function keeps
these separate:

- Mechanical source extraction and original floating-point caches.
- Exact native replay with the declared source-line rounding policy.
- The current explicitly selected rate and component boundary.
- Allocation over actual batch members, including incurred failed/repeated work.
- An empty applied-formula-repair list for this selected source mapping.

No repair is inferred from a difference. The
[workbook catalogue](table_overview.md) records broader historical exceptions;
this two-step comparison does not close them. Keep extracted observations and
comparison receipts local. Do not bundle the source workbook or generated
research data in wheels, source distributions or CI artifacts.

For a consumer rollback, select the previous installed provider release and its
unchanged legacy entry point. The historical_manual_extraction(engine) helper
calls the original engine.get_cell_value method for AB22, AB23 and AB24 on the
Labour - Usage - VCGS sheet, preserving original values, missing values and
errors. It does not reinterpret legacy output as a new Dapane report. Preserve
the reviewed input artifact and package identities with the consumer's run record.

## Qualification

The branch introduces synthetic negative/identity tests without modifying the
source workbook, immutable prepared data, dependency pins or existing quality
gates. Existing hosted checks must pass on the final provider commit. Dapane's
coordinator separately verifies installed wheels, both independently installed
provider runtimes, native CLI parity, exact reference cases, selected historical
comparisons and source/wheel identities. Until those checks are observed, this
document describes the implementation boundary, not a claim of completed
qualification.
