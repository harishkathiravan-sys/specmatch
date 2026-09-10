# V0.4 Final Dataset Audit

## Overview

This audit confirms that the active production corpus is the V0.4 FINAL dataset, and that runtime configuration and database content are aligned with it.

## Active dataset

- Dataset root: `ManakSetu_BIS_Data_V04_FINAL/ManakSetu_BIS_Data_V04_FINAL`
- Runtime app config: `backend/app/config.py`
- Active dataset version: `V0.4`
- Active DB path: `backend/specmatch.db`

## Structural validation

Executed with `backend/scripts/validate_v04_structure.py`.

Results:

- 35/35 checks passed
- 0 failed
- 0 critical failures

Key facts:

- Directory structure present and complete
- 58 required CSVs present
- standards count = 24,132
- unique `standard_id` = 24,132
- unique `standard_number` = 24,132
- no empty titles
- publication year/date checks passed
- BIS-style standard designation checks passed
- all required record-type enums were valid

## Provenance and authority validation

Executed with `backend/scripts/validate_v04_provenance.py`.

Results:

- 35/35 checks passed
- 0 failed
- 0 critical failures

Key facts:

- `record_type` distribution: `OFFICIAL_SOURCE_INVENTORY` for all standards
- `synthetic_flag` separation: all values are `False` in the official inventory
- `validation_status`: all standards are `SOURCE_DERIVED`
- `source_type`: all standards are `USER_SUPPLIED_OFFICIAL_INVENTORY`
- all standards have source attribution and source URL populated
- authoritative source registry present and valid
- registry URLs are `bis.gov.in` official URLs
- no fabricated URLs found
- quality report confirms `fabricated_authoritative_facts = 0`

## Integrity and preservation

The database integrity checks were also run against the rebuilt SQLite database and showed the expected preservation and separation:

- standards total = 24,132
- no duplicate standard IDs or numbers
- FTS count matches standards count
- status fields are populated with honest values
- unknown lifecycle/status values remain explicit instead of being converted into misleading claims

## Separation of official / derived / synthetic / unresolved

The V0.4 design is intended to separate:

- authoritative official inventory records
- source-derived fields
- inferred/derived metadata
- synthetic content (present only where explicitly labeled as synthetic)
- unresolved gaps (shown as unknown / not verified rather than fabricated)

In the current V0.4 validation pass, the active standards layer is fully `OFFICIAL_SOURCE_INVENTORY` and there are no synthetic records masquerading as official standards.

## Legacy V0.2/V0.3 references

Historical V0.2/V0.3 folders remain in the repository as archival material and are not active runtime sources. There are no route or runtime configuration references to V0.2 or V0.3 in the active application settings.

The active app config and DB are V0.4-only. Any V0.2/V0.3 references found in the repo are read-only archival artifacts or legacy schema history, not live system inputs.

## Final audit status

Status: V0.4 FINAL DATASET VERIFIED
Status: DATASET FROZEN
