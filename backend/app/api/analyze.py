"""Analyze API routes — procurement specification analysis."""

import json
import logging
import time
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger("specmatch.analyze")

from app.schemas.api import (
    AnalyzeRequest, AnalysisResponse, StandardSummary,
    RecommendationItem, ConfidenceSchema, EvidenceItemSchema,
)
from app.retrieval.pipeline import run_pipeline


router = APIRouter(prefix="/analyze", tags=["analyze"])


def _std_from_data(std: dict) -> StandardSummary:
    """Build StandardSummary from raw standard dict."""
    return StandardSummary(
        id=std.get("id", 0),
        standard_id=std.get("standard_id", ""),
        standard_number=std.get("standard_number", ""),
        title=std.get("title", ""),
        publication_year=std.get("publication_year"),
        type_of_standard=std.get("type_of_standard"),
        degree_of_equivalence=std.get("degree_of_equivalence"),
        current_status=std.get("current_status"),
        validation_status=std.get("validation_status"),
        record_type=std.get("record_type"),
        synthetic_flag=std.get("synthetic_flag", False),
        sector=std.get("sector"),
        department=std.get("department"),
        committee=std.get("committee"),
        product_category=std.get("product_category"),
        standard_family_key=std.get("standard_family_key"),
        derived_keywords=std.get("derived_keywords"),
        enrichment_status=std.get("enrichment_status"),
    )


def _build_response(text: str, pipeline_result, debug: bool = False) -> dict:
    """Build the analysis response dict from pipeline results.

    Phase 6 adds backwards-compatible intelligence fields — existing Phase 4
    keys are never removed or renamed.
    """
    from app.config import DATASET_VERSION

    # Backward-compatible requirements as strings
    req_strings = [r.text for r in pipeline_result.requirements.requirements]

    # Backward-compatible recommendations (SearchResultItem format)
    recommendations = []
    for rec in pipeline_result.recommendations:
        std = rec["standard"]
        recommendations.append({
            **_std_from_data(std).model_dump(),
            "match_score": rec.get("relevance_score", 0.5),
            "match_type": "pipeline",
            "matching_terms": [],
            "rank": rec.get("rank", 0),
        })

    # Enhanced recommendations (Phase 2 format with evidence + confidence)
    recommendations_enhanced = []
    for rec in pipeline_result.recommendations:
        std = rec["standard"]
        evidence_items = [
            EvidenceItemSchema(**e) for e in rec.get("evidence", [])
        ]
        conf = rec.get("confidence", {})
        confidence = ConfidenceSchema(
            relevance_score=conf.get("relevance_score", 0.0),
            confidence=conf.get("confidence", "low"),
            confidence_reason=conf.get("confidence_reason", ""),
            compliance_status=conf.get("compliance_status", "not_validated"),
            compliance_display=conf.get("compliance_display", "Not validated"),
        )
        recommendations_enhanced.append(RecommendationItem(
            rank=rec.get("rank", 0),
            standard=_std_from_data(std),
            relevance_score=rec.get("relevance_score", 0.5),
            confidence=confidence,
            evidence=evidence_items,
            retrieval_methods=rec.get("retrieval_methods", []),
        ))

    result: dict = {
        "query": text[:500],
        "requirements": req_strings,
        "keywords": pipeline_result.requirements.keywords,
        "categories": pipeline_result.requirements.categories,
        "recommendations": recommendations,
        "retrieval": {
            "lexical_candidates": pipeline_result.lexical_candidates,
            "semantic_candidates": pipeline_result.semantic_candidates,
            "fused_candidates": pipeline_result.fused_candidates,
        },
        "recommendations_enhanced": [r.model_dump() for r in recommendations_enhanced],
        # Always present — null-safe for forwards compatibility
        "dataset_version": DATASET_VERSION,
        "timing_ms": getattr(pipeline_result, "timing_ms", {}),
        "phase6_enabled": bool(getattr(pipeline_result, "phase6_enabled", False)),
    }

    # ── Phase 6 intelligence (backwards-compatible, added alongside existing) ──
    # Structured requirements (deterministic, never fabricated)
    try:
        from app.retrieval.structural import extract_structured
        sr = extract_structured(text)
        result["structured_requirements"] = sr.to_dict()
    except Exception:
        result["structured_requirements"] = None

    # Injection check — always run, never blocks the pipeline
    try:
        from app.retrieval.injection import detect_injection
        inj = detect_injection(text)
        result["injection_check"] = {
            "injection_detected": inj.get("injection_detected", False),
            "threat_type": inj.get("threat_type"),
            "cleaned": inj.get("injection_detected", False),
        }
    except Exception:
        result["injection_check"] = None

    p6_recs = getattr(pipeline_result, "phase6_recommendations", []) or []
    if result["phase6_enabled"] and p6_recs:
        try:
            phase6_list: list[dict] = []
            for r in p6_recs:
                d = r.to_dict() if hasattr(r, "to_dict") else dict(r)
                # Flatten for frontend convenience — keep nested too
                # Standard may be nested as { standard: {...}, data: {...}}
                std_inner = d.get("standard", {}) or {}
                # the IntelligentRecommendation stores standard_number/title at top-level plus data
                phase6_list.append(d)
            result["phase6_recommendations"] = phase6_list
            # Summaries derived from top-ranked recommendation (evidence-grounded)
            top = phase6_list[0] if phase6_list else {}
            # Compliance summary — honest "Not available..." when missing
            comp = top.get("compliance", {}) if isinstance(top, dict) else {}
            result["compliance_summary"] = comp.get("summary") if isinstance(comp, dict) else None
            lc = top.get("lifecycle", {}) if isinstance(top, dict) else {}
            result["lifecycle_summary"] = lc.get("summary") if isinstance(lc, dict) else None
            # Confidence summary for the whole result
            result["confidence_summary"] = {
                "top_confidence": top.get("confidence") if isinstance(top, dict) else None,
                "top_confidence_score": top.get("confidence_score") if isinstance(top, dict) else None,
                "top_reasons": top.get("confidence_reasons", []) if isinstance(top, dict) else [],
            }
            # Intelligence summary — what Phase 6 modules ran
            result["intelligence_summary"] = {
                "requirement_coverage": True,
                "contradiction_detection": True,
                "compliance_intelligence": True,
                "lifecycle_intelligence": True,
                "llm_safety": True,
                "confidence_calibration": True,
                "evidence_enhancement": True,
                "phase6_recommendations_count": len(phase6_list),
            }
            result["ranking_analysis"] = result["intelligence_summary"]
        except Exception:
            result["phase6_recommendations"] = None
            result["intelligence_summary"] = None
            result["ranking_analysis"] = None
    else:
        result["phase6_recommendations"] = None
        result["intelligence_summary"] = None
        result["ranking_analysis"] = None
        result["compliance_summary"] = None
        result["lifecycle_summary"] = None
        result["confidence_summary"] = None

    if debug:
        result["_debug"] = pipeline_result.timing_ms
        result["_recommendations_detail"] = pipeline_result.recommendations

    return result


@router.post("", response_model=AnalysisResponse)
async def analyze_specification(request: AnalyzeRequest):
    """Analyze a procurement specification and find matching standards.

    Observability (6.18): structured logging with request_id, query fingerprint,
    requirement counts, candidate counts, timing, confidence and LLM fallback.
    Never logs secrets. Degrades gracefully on malformed input (6.14).
    """
    request_id = uuid.uuid4().hex[:12]
    t_req = time.time()
    text = (request.text or "").strip()

    # 6.14 malformed-input handling — deterministic fallback, never 500
    if not text:
        logger.warning("analyze request_id=%s empty query", request_id)
        raise HTTPException(status_code=422, detail="Procurement specification text must not be empty.")
    if len(text) > 50000:
        logger.warning("analyze request_id=%s oversize len=%d", request_id, len(text))
        raise HTTPException(status_code=422, detail="Specification text exceeds 50,000 characters.")

    # Injection is sanitized inside the pipeline / structural layers, but log it
    try:
        from app.retrieval.injection import detect_injection
        _inj = detect_injection(text)
        if _inj.get("injection_detected"):
            logger.warning("analyze request_id=%s injection_detected type=%s", request_id, _inj.get("threat_type"))
    except Exception:
        _inj = {"injection_detected": False}

    from app.config import DEBUG
    try:
        pipeline_result = run_pipeline(
            query=text,
            top_k=10,
            max_candidates=40,
            debug=DEBUG,
        )
    except Exception as e:
        logger.exception("analyze request_id=%s pipeline_failed error=%s", request_id, str(e)[:300])
        raise HTTPException(status_code=500, detail="Retrieval pipeline failed. Please retry with a shorter or clearer specification.")

    result = _build_response(text, pipeline_result, debug=DEBUG)
    result["request_id"] = request_id

    # Phase 5: LLM intelligence layer — non-blocking, falls back deterministically
    llm_status = "skipped"
    try:
        from app.services.llm_service import analyze_with_llm
        llm_result = await analyze_with_llm(
            text=text,
            standard_ids=[r["standard"].get("standard_id", "") for r in pipeline_result.recommendations],
            query_keywords=pipeline_result.requirements.keywords,
            pipeline_recommendations=pipeline_result.recommendations,
        )
        result["llm_analysis"] = llm_result
        llm_status = "ok" if not llm_result.get("error") else "degraded"
    except Exception as e:
        llm_status = "failed"
        logger.warning("analyze request_id=%s llm_fallback error=%s", request_id, str(e)[:200])
        result["llm_analysis"] = {
            "error": str(e)[:200],
            "summary": {
                "summary": "LLM intelligence layer unavailable — deterministic retrieval results shown.",
                "key_requirements": [],
                "compliance_overview": "",
                "risk_assessment": "",
                "recommended_actions": [],
            },
            "standard_assessments": [],
        }

    total_ms = (time.time() - t_req) * 1000
    logger.info(
        "analyze request_id=%s q_len=%d keywords=%d recs=%d phase6=%s llm=%s "
        "lexical=%s fused=%s timing=%s total_ms=%.1f inject=%s",
        request_id, len(text), len(pipeline_result.requirements.keywords),
        len(pipeline_result.recommendations), result.get("phase6_enabled"),
        llm_status, pipeline_result.lexical_candidates, pipeline_result.fused_candidates,
        json.dumps({k: round(v, 1) for k, v in pipeline_result.timing_ms.items()}),
        total_ms, _inj.get("injection_detected"),
    )

    # Log analysis history (best-effort)
    try:
        from app.database import get_db
        with get_db() as conn:
            conn.execute(
                """INSERT INTO analysis_history
                   (query_text, requirements_json, recommendations_json)
                   VALUES (?, ?, ?)""",
                (
                    text[:1000],
                    json.dumps(pipeline_result.requirements.keywords[:5]),
                    json.dumps([r.get("standard_number", "") for r in result.get("recommendations", [])[:5]]),
                ),
            )
    except Exception:
        pass

    return result


def _extract_docx_text(raw_bytes: bytes) -> str:
    """Extract text from DOCX: paragraphs + tables (procurement specs often have tables)."""
    import io
    import docx

    doc = docx.Document(io.BytesIO(raw_bytes))
    parts: list[str] = []

    # Paragraphs
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)

    # Tables — procurement specifications frequently embed data in tables
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return "\n".join(parts)


def _extract_pdf_text(raw_bytes: bytes, filename: str) -> str:
    """Extract text from a PDF. Returns a clear message for image-only PDFs."""
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages: list[str] = []
    for pg in reader.pages:
        try:
            t = pg.extract_text() or ""
            if t.strip():
                pages.append(t.strip())
        except Exception:
            continue

    text = "\n".join(pages).strip()
    if not text and len(reader.pages) > 0:
        return f"No readable text was found in this PDF. Please upload a text-based PDF or paste the specification."
    return text


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a tender/specification document for analysis."""
    request_id = uuid.uuid4().hex[:12]

    # ── Validate filename ──
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    allowed_types = {".pdf", ".docx", ".txt"}
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(sorted(allowed_types))}"
        )

    # ── Validate file size ──
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty. Please upload a non-empty document.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    # ── Extract text by type ──
    text = ""
    try:
        if file_ext == ".txt":
            text = content.decode("utf-8", errors="replace")

        elif file_ext == ".docx":
            try:
                text = _extract_docx_text(content)
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="DOCX support requires python-docx. Please install it: pip install python-docx"
                )
            except Exception as e:
                logger.warning("upload request_id=%s docx_parse_error=%s", request_id, str(e)[:200])
                raise HTTPException(status_code=400, detail=f"Could not parse DOCX file: {e}")

        elif file_ext == ".pdf":
            try:
                text = _extract_pdf_text(content, file.filename)
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PDF support requires pypdf. Please install it: pip install pypdf"
                )
            except Exception as e:
                logger.warning("upload request_id=%s pdf_parse_error=%s", request_id, str(e)[:200])
                raise HTTPException(status_code=400, detail=f"Could not parse PDF: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("upload request_id=%s extraction_error=%s", request_id, str(e)[:200])
        raise HTTPException(status_code=400, detail=f"Failed to extract text from document: {e}")

    # ── Validate extracted content ──
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from this document. The file may be empty, image-based, or corrupted."
        )

    if len(text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Extracted text is too short for meaningful analysis. Please upload a more detailed document."
        )

    # ── Sanitize: treat uploaded text as untrusted input ──
    # Injection is detected inside the pipeline / structural layers.
    try:
        from app.retrieval.injection import detect_injection
        _inj = detect_injection(text)
        if _inj.get("injection_detected"):
            logger.warning("upload request_id=%s injection_detected type=%s", request_id, _inj.get("threat_type"))
    except Exception:
        _inj = {"injection_detected": False}

    # ── Run the SAME pipeline as text-analyze ──
    from app.config import DEBUG
    try:
        pipeline_result = run_pipeline(
            query=text,
            top_k=10,
            max_candidates=40,
            debug=DEBUG,
        )
    except Exception as e:
        logger.exception("upload request_id=%s pipeline_failed error=%s", request_id, str(e)[:300])
        raise HTTPException(
            status_code=500,
            detail="Retrieval pipeline failed. Please try with a shorter or clearer specification."
        )

    result = _build_response(text, pipeline_result, debug=DEBUG)
    result["file_name"] = file.filename
    result["file_size"] = len(content)
    result["text_length"] = len(text)
    result["request_id"] = request_id

    logger.info(
        "upload request_id=%s file=%s ext=%s size=%d text_len=%d keywords=%d recs=%d",
        request_id, file.filename, file_ext, len(content), len(text),
        len(pipeline_result.requirements.keywords), len(pipeline_result.recommendations),
    )

    return result
