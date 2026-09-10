# SpecMatch / ManakSetu BIS Dataset V0.4 FINAL

Build date: 2026-09-06
Base: V0.3
Status: FINAL DATASET FREEZE

## Purpose
V0.4 is the final research/enrichment dataset freeze for the SpecMatch procurement-intelligence system.
It preserves the full V0.3 inventory and adds a governed authoritative-source layer, compliance/legal framework,
certification-scheme registry, procurement technical-attribute ontology, evidence-graph relationship schema,
multilingual authority policy, query-expansion governance, validation matrix, and quality audit.

## Authority policy
1. BIS sources are the preferred authoritative source for standard lifecycle, amendments, references,
   certification, QCO and conformity-assessment facts.
2. A field is never promoted to authoritative merely because it can be inferred from a title.
3. Synthetic and derived records remain labelled.
4. Unknown/current-status fields remain unknown when no authoritative record was captured.
5. Application relevance is an AI/retrieval inference and is not treated as a BIS legal determination.
6. QCO applicability must be checked against the current QCO/gazette evidence available at decision time.

## Key authoritative sources
- BIS Know Your Standard
- BIS Standards Portal
- BIS Product Certification Scheme I
- BIS Upcoming QCOs
- BIS Act, Rules & Regulations
- BIS Product Certification / FAQ
- BIS Scheme X FAQ
- BIS Compendium of Indian Standards
- BIS Standards India
- BIS QCO primary gazette example

## Finality
No V0.5 dataset is planned. Any future changes should be handled as timestamped source refreshes,
incremental updates, or a new release only if the underlying official BIS inventory itself changes materially.

## Important limitation
The 24,132-record inventory remains preserved from the published standards source supplied in V0.3.
V0.4 does NOT pretend that every standard's detailed BIS portal page has been independently scraped.
Instead, it creates a complete authority-enrichment index so the application can distinguish:
inventory-confirmed records, individually verified authority records, derived fields, and unresolved enrichment.
