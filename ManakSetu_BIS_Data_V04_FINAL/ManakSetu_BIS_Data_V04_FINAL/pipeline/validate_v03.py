from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
std=pd.read_csv(ROOT/'01_core/standards.csv')
qco=pd.read_csv(ROOT/'02_compliance/qco.csv')
assert len(std)==24132, len(std)
assert std.standard_number.nunique()==24132
assert len(qco)==28
assert (ROOT/'00_raw/source_manifest.csv').exists()
assert (ROOT/'11_quality/qa_results_v03.csv').exists()
print('V0.3 validation PASSED')
print('standards:',len(std),'unique:',std.standard_number.nunique(),'QCO rows:',len(qco))
