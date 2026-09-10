# SpecMatch — Standards Intelligence for Procurement

> **Given this procurement requirement, which Indian Standards are most relevant, and why?**

SpecMatch searches the **ManakSetu BIS Published Standards** corpus (24,132 standards, V0.3 FINAL) and returns ranked, evidence-grounded recommendations with transparent provenance and compliance intelligence.

**Do NOT rename the dataset.** `SpecMatch_Data_V03_FINAL/ManakSetu_BIS_Data_V03/` is the source of truth.

---

## Provenance & Compliance Honesty (critical)

Do **not** collapse categories. Every field that is not authoritatively validated declares it:

- **Official / source-derived** — `validation_status = SOURCE_DERIVED`, `record_type = OFFICIAL_SOURCE_INVENTORY`
- **Inferred** — `INFERRED_NOT_OFFICIAL` + `enrichment_status = DERIVED_V02` (e.g. `derived_keywords`, `standard_family_key`, `scope_inferred`)
- **Synthetic** — `SYNTHETIC` / `synthetic_flag = true` (benchmarks, synthetic tenders — never mixed into official results without label)
- **Missing authoritative enrichment** — `NOT_VALIDATED` + `NEEDS_AUTHORITATIVE_*` (e.g. `qco_validation_status = NEEDS_GOVERNMENT_SOURCE`, `cert_validation_status = NEEDS_AUTHORITATIVE_BIS_SOURCE`, `amendment_validation_status = NEEDS_AUTHORITATIVE_ENRICHMENT`). UI copy: *“QCO applicability has not been validated in the current dataset”* — not *“No QCO applies”*.

---

## Architecture

```
SpecMatch_Data_V03_FINAL/ManakSetu_BIS_Data_V03/   24,132 official records + 47+ CSVs (provenance-aware)
backend/                             FastAPI + SQLite (FTS5) → Postgres+pgvector target
  app/api/  standards.py  search.py  analyze.py
  app/services/standards_service.py
  app/retrieval/search_service.py    FTS5 OR-joined recall + snippet/highlight fallback LIKE
  scripts/schema.sql                 SQLite + FTS5 + application tables
  scripts/import_dataset.py          idempotent CSV → DB + FTS rebuild
  scripts/evaluate_retrieval.py      benchmark harness (Recall@K, MRR)
  scripts/migrate_pgvector.py        PG delta (vector/HNSW + tsvector)
frontend/                            React 19 + Vite 8 + TypeScript + Tailwind 4 + react-router
  src/pages/  Home Search Analyze Standards StandardDetail Compare Saved History Methodology
  src/services/api.ts                typed fetch layer
  vite.config.ts                     /api → 127.0.0.1:8000 proxy
```

Current deployment can use **SQLite + FTS5** locally or **Supabase PostgreSQL** with PostgreSQL full-text search and pgvector.

---

## Stack

- **Backend:** Python 3.14, FastAPI 0.115, Uvicorn, Pydantic 2.9, aiosqlite, pypdf 4.2, python-docx 1.1, httpx
- **Frontend:** React 19, Vite 8, TypeScript 6, Tailwind CSS 4, lucide-react, react-router-dom 7
- **Data:** SQLite + FTS5 (`porter unicode61`), future: Postgres `vector(384)` / `tsvector` + HNSW
- **Eval:** `09_evaluation/benchmark.csv` (2,000) + `metrics.py` (Recall@K, MRR)

---

## Quickstart

### 1. Prerequisites

- Python 3.12+ and Node 20+
- Dataset at `../SpecMatch_Data_V03_FINAL/ManakSetu_BIS_Data_V03/`

### 2. Backend

```bash
cd backend
python -m pip install -r requirements.txt   # includes pypdf (PDF), python-docx (DOCX), python-multipart (upload)
python scripts/import_dataset.py        # builds specmatch.db (120.9 MB) + FTS index
python -m uvicorn app.main:app --reload --port 8000 --app-dir .
# health: http://127.0.0.1:8000/api/health
# docs:   http://127.0.0.1:8000/docs
```

Re-import is idempotent — rerun `import_dataset.py` any time.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173  (proxies /api to :8000)
npm run build        # production build — must pass with no TS errors
npm run preview
```

---

### 4. Environment

Copy `.env.example` to `.env` (all keys optional for local dev):

```
DATABASE_URL=sqlite:///backend/specmatch.db
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EMBEDDING_PROVIDER=        # openai|cohere|local (Phase 3)
VECTOR_DIMENSION=384
```

For Supabase, set `DATABASE_URL` in `backend/.env` to the direct PostgreSQL
connection string from Supabase. Never commit that file or expose the password
to the frontend.

---

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/health` | `database_size_mb`, `connected` |
| GET | `/api/standards/stats` | 24132, year range, types |
| GET | `/api/standards/filters` | sectors/departments/committees/types/years/statuses |
| GET | `/api/standards?page=&page_size=&sector=&type_of_standard=&sort_by=&sort_dir=` | paginated directory |
| GET | `/api/standards/{IS number}` | detail + relationships + family + references + QCO/cert/amendments |
| POST | `/api/standards/compare` | `{ standard_ids: string[2..3] }` → `{ standards, differences }` |
| POST | `/api/standards/saved` | bookmark; `GET /api/standards/saved/list`, `DELETE /api/standards/saved/{id}` |
| GET | `/api/standards/history/list?limit=` | search history |
| GET | `/api/search?q=&page=&page_size=&sector=&type_of_standard=&year_from=&year_to=&status=` | FTS5 OR + snippet |
| POST | `/api/analyze` | `{ text }` → `{ requirements, keywords, categories, recommendations }` |
| POST | `/api/analyze/upload` | multipart `.pdf/.docx/.txt` up to **10 MB** (pypdf, python-docx). DOCX includes paragraph + table text. |

Search uses OR-joined normalized terms for long procurement sentences so partial matches are returned (recall-first), with `matching_terms` + `snippet` (`<mark>`) for evidence.

---

## Frontend Routes

`/`, `/search`, `/analyze`, `/standards`, `/standards/:id`, `/compare?ids=IS ...`, `/saved`, `/history`, `/methodology`

Design: restrained palette `--brand #1a4d3e`, charcoal text, Inter, evidence-first cards with `ProvenanceBadge` — no purple gradients.

---

## Evaluation

Ground-truth harness — no fabricated scores. Run:

```bash
python scripts/evaluate_retrieval.py            # full 2,000
python scripts/evaluate_retrieval.py --limit 100
```

Current FTS baseline (measured `2026-09-04` on this machine):

```
Evaluated: 100 queries
Recall@1: 0.9900
Recall@5: 1.0000
Recall@10: 1.0000
MRR: 0.9949
```

Benchmark is synthetic title-match — real procurement phrasing will score lower; vector + reranker (Phase 3) closes the gap. Use `scripts/evaluate_retrieval.py` as the single source of truth for any reported metric.

---

## PDF / DOCX Upload

- `.txt` — `utf-8` decode
- `.docx` — `python-docx` paragraph join
- `.pdf` — `pypdf` (`PdfReader` per-page `extract_text()`); scanned/image PDFs return an explicit notice. Encrypted PDFs return 400.

Install extras: `pip install pypdf python-docx` (in `requirements.txt`).

---

## Supabase PostgreSQL Migration

Install the backend dependencies, put the Supabase direct connection string in
`backend/.env`, then run from `backend/`:

```bash
python -m pip install -r requirements.txt
python scripts/migrate_supabase.py
```

The migration creates the relational schema, imports all dataset CSVs, builds
the PostgreSQL `tsvector`/GIN search index, and enables the `vector(384)`/
HNSW column for future embeddings. It is repeatable; use
`python scripts/migrate_supabase.py --reset` only for an intentional reload.
The backend automatically selects Supabase when `DATABASE_URL` starts with
`postgresql://` and retains SQLite + FTS5 for local fallback.

---

## Project Layout

```
D:\testing2\
  ManakSetu_BIS_Data_V02_FINAL/  # do not rename
  backend/specmatch.db           # generated (not committed)
  .env.example
  README.md
```

---

## Limitations & Disclaimer

- QCO / certification / amendments are **NOT authoritative** in V02 — shown as “not validated / needs enrichment”.
- `scope`, `product_category`, family parsing are derived from the title only.
- This project does not claim BIS endorsement; always verify against the official BIS catalogue before procurement decisions.

---

## License

Dataset per source terms; code as configured for the consuming project.
