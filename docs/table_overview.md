# Workbook table catalogue

This replaces the earlier overview, which omitted sheets and overstated complete validation. The selected v15 workbook has **35 worksheets, zero formal Excel Table objects and 36,411 formula cells**. Worksheet IDs below refer to this exact workbook order/version, not durable identities across workbook revisions. Logical blocks within sheets require region-level classification in the parameter provenance track.

Source SHA-256: `2990ff57504a51c5a9152b053a8e7cfa0e490f27a75bb356810f3564f96b5eb4`. All 35 sheets are incorporated by the existing SheetManager native value/formula interfaces. A read-only check compared **188,268 cells** below configured headers in both cached and formula frames, expanding merged anchors, with **zero ingestion mismatches**. Numeric int/float equivalents were accepted; boolean identity was retained. The source file hash was unchanged. This is ingestion proof, not recalculation, provenance validation or scientific acceptance.

The parser fallback for unconfigured sheets uses one header row/data from row two. That provides access; it does not establish the correct semantic schema for every multi-block sheet. Prepared filename presence is not a source-bound validation receipt. No workbook, oracle or prepared table was regenerated for this catalogue.

## Complete worksheet register

| ID | Worksheet | Source extent (rows × columns) | Formulas | Role and interpretation |
|---|---|---:|---:|---|
| WB01 | At a Glance | 47 × 10 | 0 | Stage/sub-stage/component map across equipment, consumables and labour; descriptive, not a computed cost table. |
| WB02 | Summary Table | 81 × 16 | 763 | Cost summary linked to Detailed Table and storage usage; do not add it to its component inputs. |
| WB03 | Summary 20230812 | 99 × 11 | 0 | Dated static summary; no formulas. Preserve as historical evidence, not the current calculation oracle. |
| WB04 | Summ Tab by Cat | 81 × 16 | 763 | Category-oriented cost summary; shares detailed/storage dependencies with other summaries. |
| WB05 | Summ Tab by Stage | 81 × 80 | 763 | Stage-oriented presentation with multiple column blocks; preserve all 80 source columns. |
| WB06 | Summ Table for Graph | 76 × 16 | 765 | Graph-oriented summary; retain ordering and denominator interpretation before plotting. |
| WB07 | Summary Table 2 | 75 × 18 | 642 | Alternate detailed-cost aggregation; distinguish it from similarly named summary editions. |
| WB08 | Summary Table Ordered | 294 × 26 | 642 | Ordered test/category/stage rows with subtotal rows. Stage and subtotal costs must not both be counted. |
| WB09 | Sheet1 | 56 × 5 | 114 | Category/stage LL/MP/UL working summary linked to Detailed Table; not an unidentified disposable sheet. |
| WB10 | DSA - Summary | 25 × 31 | 220 | DSA aggregation of overhead, consumable discount, throughput and labour-price branches. |
| WB11 | DSA - Tornado (index 0) | 18 × 17 | 210 | Zero-index-labelled tornado representation; exact baseline/index interpretation remains to be documented. |
| WB12 | DSA - Tornado (index actual) | 18 × 17 | 210 | Actual-index-labelled tornado representation; keep separate from zero-index and actual-cost versions. |
| WB13 | DSA - Tornado Actual | 25 × 33 | 220 | Actual-cost-labelled tornado comparison across DSA branches; not independent observations. |
| WB14 | DSA - Differences | 27 × 31 | 230 | Differences between scenario results; verify sign and denominator before ranking. |
| WB15 | DSA - Summary (2) | 33 × 31 | 220 | Alternate DSA summary edition; preserve identity and compare lineage before deduplication. |
| WB16 | DSA - Summary - Stats | 25 × 6 | 60 | Relative numerator/denominator assay matrix referencing DSA summary; do not infer a generic statistical model from its name. |
| WB17 | Detailed Table | 1340 × 27 | 16,605 | Detailed microcosting formulas by test/category/sub-category/step; 1,336 rows below four headers include non-detail rows, not 1,336 proven process steps. |
| WB18 | Process | 39 × 2 | 0 | Stage/step reference table; descriptive baseline topology. |
| WB19 | DSA - Overheads | 81 × 31 | 1,467 | Overhead scenario branch over detailed costs; retain accounting base and avoid duplicate overhead allocation. |
| WB20 | DSA - Overheads (USD) | 81 × 31 | 1,496 | USD-labelled overhead branch with additional resource dependencies; verify actual currency/FX lineage before reuse. |
| WB21 | Sheet2 | 11 × 6 | 0 | Stage-by-assay matrix without formulas; units, origin and intended use require explicit classification. |
| WB22 | DSA - Consumable Discounts | 81 × 34 | 1,422 | Consumable-discount scenarios over detailed costs; not procurement-price evidence by itself. |
| WB23 | DSA - Cons Discounts (USD) | 81 × 34 | 1,422 | USD-labelled consumable discount branch; retain currency and conversion assumptions separately. |
| WB24 | DSA - Test Throughput | 81 × 34 | 1,512 | Test-throughput scenarios over detailed costs; volume sensitivity is not a validated queue/batch optimizer. |
| WB25 | DSA - Labour Prices | 81 × 52 | 2,550 | Labour-price scenarios across assays/jurisdictions; preserve price basis and role mappings. |
| WB26 | Process - WES+Panel - VCGS | 58 × 3 | 0 | WES/panel process description; distinguish physical steps, resources and narrative annotations. |
| WB27 | Process - WGS - VCGS | 54 × 3 | 0 | WGS process description; preserve this separate workflow and its resource requirements. |
| WB28 | Labour - Costs - VCGS | 31 × 30 | 186 | Labour cost assumptions/rates and costing bases; source dates and on-cost interpretation need parameter-level provenance. |
| WB29 | Labour - Usage - VCGS | 111 × 41 | 1,928 | Labour usage by process/test linked to labour cost inputs; distinguish hands-on, elapsed and shared time. |
| WB30 | Cons -  Costs and Util - VCGS | 120 × 17 | 442 | Consumable items, prices and usage with computed cells; distinguish unit price, pack size, wastage and per-test consumption. |
| WB31 | Eq - Usage - VCGS | 53 × 28 | 478 | Equipment usage linked to equipment costs; preserve shared capacity and allocation assumptions. |
| WB32 | Eq - Costs and Usage - VCGS | 63 × 33 | 176 | Equipment costs and usage/annualisation assumptions; distinguish purchase, replacement, useful life, utilization and maintenance. |
| WB33 | BI - Comp+Stor Costs - VCGS | 34 × 29 | 51 | Combined bioinformatics compute/storage cost inputs; distinguish rate, allocation and price-period bases. |
| WB34 | BI - Comp Use - VCGS | 126 × 23 | 660 | Compute usage linked to combined rates; requested/allocated resources are not automatically measured/billed usage. |
| WB35 | BI - Stor Use - VCGS | 47 × 18 | 194 | Storage usage linked to combined rates; retain volume, copies, retention and time denominator. |

## What the workbook contains

The baseline is a process/resource microcosting model: workflow descriptions and identifiers, labour/equipment/consumable quantities and rates, compute/storage use and rates, formula-based detailed costs, scenario branches, summaries, graph inputs and historical/manual matrices. These are different evidential roles. Summaries and sensitivity outputs must not become additional independent cost inputs or independent observations. An archived scenario distribution is not automatically an empirically fitted uncertainty distribution.

Observed literal formula dependencies establish the main chain: labour rates → labour usage; equipment rates → equipment usage; combined compute/storage rates → usage sheets; these resources → Detailed Table → summaries. Overhead/discount/throughput/labour-price DSA branches feed DSA summaries and tornado/difference views. Some summaries also reference storage directly, so a simple single-hub diagram is incomplete. The JSON companion records literal references; INDIRECT/dynamic/external-reference completeness has not been established.

Different source names (including WES/WEA/EA and trio/proband labels) must be preserved until a documented assay mapping establishes equivalence. Blank/zero/dash/error, currency, time and cost-denominator meanings must remain distinct. The apparent Sheet1 and Sheet2 utilities now have explicit roles and unresolved semantic questions rather than being dropped.

## Remaining qualification and change boundaries

The historical full-workbook replay classified three broken references and four division-error policies. Four missing subtotal valuations and branch/additivity qualification remain open. The new inventory does not close those issues or certify every logical block, formula, distribution or parameter. Full conditional/default/named-range/validation/comment and region extraction is an explicit deliverable of the provenance track.

Candidate processes, updated parameters, batch policies and compute models each carry their own version and provenance. See the [machine-readable workbook catalogue](workbook_catalog.json) for the worksheet and cell inventory.
