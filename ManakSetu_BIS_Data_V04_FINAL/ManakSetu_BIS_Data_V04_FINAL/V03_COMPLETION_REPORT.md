# ManakSetu BIS Data V0.3 — Completion Report

Generated: 2026-09-05

## Purpose
V0.3 upgrades V0.2 from a source-derived inventory into a provenance-aware procurement intelligence dataset. It preserves all V0.2 records and adds authoritative BIS source references, lifecycle events, QCO mappings, compliance provenance, retrieval hard negatives, evidence spans, validation queues, multilingual scaffolds, and stronger evaluation structures.

## Core integrity
- 24,132 canonical standards retained.
- V0.2 is preserved as the base; V0.3 does not overwrite it.
- Unknown values remain explicit as `NOT_AVAILABLE`, `NOT_VALIDATED`, or `NEEDS_*`.
- No expert labels or translations were fabricated.

## Authoritative enrichment captured
- BIS Know Your Standard portal reference.
- BIS Products under Compulsory Certification policy reference.
- BIS Upcoming QCO table: 28 rows captured as of the source page last update of 4 August 2026.
- QCO-to-standard mappings preserve unmatched standards as `NOT_IN_V02_INVENTORY` rather than inventing a standard record.

## Retrieval improvements
- Hard-negative candidates generated from lexical similarity and marked synthetic / requiring expert validation.
- Query expansion layer generated from titles and explicitly marked auxiliary/non-authoritative.
- Evidence spans added for source inventory titles.

## Validation
V0.3 includes validation queues, source conflict structure, enrichment coverage, source coverage, and QA reports.

## Important limitation
V0.3 is **not** a claim that all 24,132 standards have been individually enriched from BIS Know Your Standard. The official portal is cataloged and the dataset is structured for such enrichment; only source-backed QCO rows visible on the official BIS upcoming-QCO page were concretely captured in this release.
