"""Rebuilds the V0.3 structure from a V0.2 directory plus the captured official-source CSVs.
This release intentionally does not scrape live BIS pages at build time; source snapshots/references are explicit inputs.
"""
from pathlib import Path
print("V0.3 build specification is data-first. Use the supplied V0.2 base and 00_raw/source_manifest.csv, then rerun enrichment modules as new official snapshots are captured.")
