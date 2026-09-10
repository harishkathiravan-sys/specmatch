"""SpecMatch — Standards Intelligence for Procurement.

FastAPI backend for the SpecMatch application.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_PREFIX, CORS_ORIGINS, DEBUG, DB_PATH, IS_POSTGRES
from app.api import standards, search, analyze, llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown events."""
    # Startup: verify the configured database is reachable.
    if IS_POSTGRES:
        from app.database import get_db
        try:
            with get_db() as conn:
                conn.execute("SELECT 1")
        except Exception as exc:
            print(f"WARNING: PostgreSQL database unavailable: {exc}")
    elif not DB_PATH.exists():
        print(f"WARNING: Database not found at {DB_PATH}")
        print("Run: python scripts/import_dataset.py")
    yield


app = FastAPI(
    title="SpecMatch API",
    description="Standards Intelligence for Procurement — BIS Standards Corpus API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(standards.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(analyze.router, prefix=API_PREFIX)
app.include_router(llm.router, prefix=API_PREFIX)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    from app.config import DATASET_VERSION, STANDARDS_COUNT, DATA_DIR, IS_POSTGRES
    if IS_POSTGRES:
        from app.database import get_db
        try:
            with get_db() as conn:
                count = conn.execute("SELECT COUNT(*) AS count FROM standards").fetchone()["count"]
            db_exists = True
            db_size = 0
        except Exception:
            count = 0
            db_exists = False
            db_size = 0
    else:
        count = 0
        db_exists = DB_PATH.exists()
        db_size = DB_PATH.stat().st_size if db_exists else 0
    return {
        "status": "healthy" if db_exists else "degraded",
        "database": "connected" if db_exists else "not_found",
        "database_size_mb": round(db_size / 1024 / 1024, 1),
        "version": "0.1.0",
        "dataset_version": DATASET_VERSION,
        "standards_count": STANDARDS_COUNT,
        "standards_loaded": count,
        "data_dir": str(DATA_DIR),
        "llm_enabled": bool(os.getenv("OPENROUTER_API_KEY")),
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "SpecMatch API",
        "version": "0.1.0",
        "description": "Standards Intelligence for Procurement",
        "docs": "/docs",
        "health": "/api/health",
    }
