"""LLM Intelligence Service — OpenRouter integration (Phase 5).

Transforms SpecMatch from dataset-backed search into evidence-grounded
procurement standards intelligence by adding an LLM analysis layer.

Architecture:
  React → FastAPI → OpenRouter (never React → OpenRouter directly)

All LLM calls go through this service. The API key is NEVER exposed
to the frontend — it lives only in backend environment variables.
"""

import hashlib
import json
import time
from typing import Optional

import httpx

from app.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MAX_TOKENS,
    OPENROUTER_MODEL,
    OPENROUTER_TEMPERATURE,
)


# ------------------------------------------------------------------
# Prompt templates
# ------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """You are SpecMatch Intelligence — an expert system for Indian Bureau of Standards (BIS) procurement standards analysis.

Your role:
1. Analyze procurement specifications against the Indian Standards corpus
2. Assess relevance, compliance status, and risk for each recommended standard
3. Provide evidence-grounded, actionable procurement intelligence

Rules:
- Only reference standards that are in the provided context
- Clearly distinguish between verified compliance and unvalidated claims
- Flag any procurement risks (expired standards, missing certifications, ambiguous scope)
- Use authoritative language: cite standard numbers, not vague descriptions
- When uncertain, say so — never fabricate compliance status
- Keep responses structured and concise for procurement officers"""

ANALYSIS_USER_TEMPLATE = """Analyze this procurement specification for relevant Indian Standards:

---
{specification_text}
---

{context_section}

Provide your analysis as JSON with this exact structure:
{{
  "summary": {{
    "summary": "2-3 sentence executive summary",
    "key_requirements": ["requirement 1", "requirement 2", ...],
    "compliance_overview": "Brief overview of compliance landscape",
    "risk_assessment": "Key risks identified",
    "recommended_actions": ["action 1", "action 2", ...]
  }},
  "standard_assessments": [
    {{
      "standard_id": "standard_id from context",
      "standard_number": "IS XXXXX",
      "relevance_explanation": "Why this standard is relevant",
      "compliance_note": "Compliance requirements if any",
      "risk_flags": ["risk 1", ...],
      "recommendation": "recommend|consider|not_relevant",
      "confidence": "high|medium|low"
    }}
  ]
}}"""


def _build_context_section(
    standard_ids: list[str],
    query_keywords: list[str],
    pipeline_recommendations: list[dict] | None = None,
) -> str:
    """Build context section for the LLM prompt from retrieval results."""
    lines = []

    if query_keywords:
        lines.append(f"Extracted keywords: {', '.join(query_keywords[:10])}")
        lines.append("")

    if pipeline_recommendations:
        lines.append("Retrieved standards (ranked by relevance):")
        for i, rec in enumerate(pipeline_recommendations[:10], 1):
            std = rec.get("standard", {})
            sn = std.get("standard_number", "Unknown")
            title = std.get("title", "")
            score = rec.get("relevance_score", 0)
            evidence = rec.get("evidence", [])
            evidence_str = "; ".join(e.get("evidence_text", "") for e in evidence[:3]) if evidence else "N/A"
            compliance = rec.get("confidence", {}).get("compliance_status", "not_validated")

            lines.append(f"  {i}. {sn} — {title}")
            lines.append(f"     Relevance: {score:.2f} | Compliance: {compliance}")
            lines.append(f"     Evidence: {evidence_str}")
            lines.append("")
    elif standard_ids:
        lines.append(f"Retrieved standard IDs: {', '.join(standard_ids[:10])}")

    return "\n".join(lines) if lines else "No retrieval context available."


def _get_cache_key(text: str, model: str, has_pipeline_context: bool = False) -> str:
    """Generate a deterministic cache key for the query + model + context."""
    ctx = "pipelined" if has_pipeline_context else "standalone"
    raw = f"{model}:{ctx}:{text[:2000]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _check_cache(cache_key: str) -> Optional[dict]:
    """Check the in-memory cache (lightweight — use SQLite for production)."""
    import sqlite3
    from app.config import DB_PATH
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.execute(
            "SELECT analysis_json, model_used FROM llm_analysis_cache WHERE query_hash = ?",
            (cache_key,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"analysis": json.loads(row[0]), "model_used": row[1]}
    except Exception:
        pass
    return None


def _store_cache(cache_key: str, text: str, model: str, analysis: dict) -> None:
    """Store analysis in the cache."""
    import sqlite3
    from app.config import DB_PATH
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            """INSERT OR REPLACE INTO llm_analysis_cache
               (query_hash, query_text, model_used, analysis_json)
               VALUES (?, ?, ?, ?)""",
            (cache_key, text[:1000], model, json.dumps(analysis)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


async def analyze_with_llm(
    text: str,
    standard_ids: list[str] | None = None,
    query_keywords: list[str] | None = None,
    pipeline_recommendations: list[dict] | None = None,
    use_cache: bool = True,
) -> dict:
    """Call OpenRouter LLM to analyze a procurement specification.

    Returns a dict with keys: model_used, summary, standard_assessments,
    raw_response, tokens_used, latency_ms, cached.
    """
    model = OPENROUTER_MODEL
    has_context = bool(pipeline_recommendations)
    cache_key = _get_cache_key(text, model, has_context)

    # Check cache
    if use_cache:
        cached = _check_cache(cache_key)
        if cached:
            return {
                **cached["analysis"],
                "cached": True,
            }

    # Check if API key is available
    if not OPENROUTER_API_KEY:
        return {
            "model_used": model,
            "summary": {
                "summary": "LLM intelligence layer is not configured. Add OPENROUTER_API_KEY to enable AI-powered analysis.",
                "key_requirements": [],
                "compliance_overview": "Configure OPENROUTER_API_KEY environment variable to enable LLM analysis.",
                "risk_assessment": "N/A",
                "recommended_actions": ["Set OPENROUTER_API_KEY in .env file"],
            },
            "standard_assessments": [],
            "raw_response": "",
            "tokens_used": 0,
            "latency_ms": 0,
            "cached": False,
            "error": "OPENROUTER_API_KEY not configured",
        }

    # Build prompt
    context_section = _build_context_section(
        standard_ids or [],
        query_keywords or [],
        pipeline_recommendations,
    )
    user_prompt = ANALYSIS_USER_TEMPLATE.format(
        specification_text=text[:8000],
        context_section=context_section,
    )

    # Call OpenRouter
    start_ms = int(time.time() * 1000)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://specmatch.app",
                    "X-Title": "SpecMatch Intelligence",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": OPENROUTER_MAX_TOKENS,
                    "temperature": OPENROUTER_TEMPERATURE,
                },
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        return {
            "model_used": model,
            "summary": {
                "summary": "LLM analysis timed out. The specification may be too long for real-time analysis.",
                "key_requirements": [],
                "compliance_overview": "",
                "risk_assessment": "Analysis timeout",
                "recommended_actions": ["Try a shorter specification", "Retry later"],
            },
            "standard_assessments": [],
            "raw_response": "",
            "tokens_used": 0,
            "latency_ms": int(time.time() * 1000) - start_ms,
            "cached": False,
            "error": "timeout",
        }
    except httpx.HTTPStatusError as e:
        return {
            "model_used": model,
            "summary": {
                "summary": f"LLM service returned an error (HTTP {e.response.status_code}).",
                "key_requirements": [],
                "compliance_overview": "",
                "risk_assessment": "Service error",
                "recommended_actions": ["Check API key validity", "Retry later"],
            },
            "standard_assessments": [],
            "raw_response": str(e)[:500],
            "tokens_used": 0,
            "latency_ms": int(time.time() * 1000) - start_ms,
            "cached": False,
            "error": f"HTTP {e.response.status_code}",
        }
    except Exception as e:
        return {
            "model_used": model,
            "summary": {
                "summary": f"LLM analysis failed: {str(e)[:200]}",
                "key_requirements": [],
                "compliance_overview": "",
                "risk_assessment": "Service error",
                "recommended_actions": ["Retry later"],
            },
            "standard_assessments": [],
            "raw_response": "",
            "tokens_used": 0,
            "latency_ms": int(time.time() * 1000) - start_ms,
            "cached": False,
            "error": str(e)[:500],
        }

    elapsed_ms = int(time.time() * 1000) - start_ms

    # Parse response
    data = response.json()
    raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    tokens_used = data.get("usage", {}).get("total_tokens", 0)

    # Parse the JSON from the LLM — handle multiple common patterns
    import re
    analysis = None

    def _try_parse_json(s: str) -> dict | None:
        """Try to parse a string as JSON, return dict or None."""
        try:
            result = json.loads(s)
            return result if isinstance(result, dict) else None
        except (json.JSONDecodeError, ValueError):
            return None

    def _is_valid_analysis(d: dict) -> bool:
        """Check if a dict has the expected LLM analysis structure."""
        if "summary" not in d:
            return False
        s = d["summary"]
        if isinstance(s, str):
            return len(s) > 20
        if isinstance(s, dict):
            return "summary" in s and len(str(s.get("summary", ""))) > 20
        return False

    # Strategy 1: Direct parse of the full content
    analysis = _try_parse_json(raw_content.strip())

    # Strategy 2: Strip markdown code fences
    if analysis is None or not _is_valid_analysis(analysis):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_content.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        analysis = _try_parse_json(cleaned)

    # Strategy 3: Try progressively smaller substrings — find valid JSON blocks
    if analysis is None or not _is_valid_analysis(analysis):
        # Find all positions of '{' and try parsing from each
        for i, ch in enumerate(raw_content):
            if ch == '{':
                for j in range(len(raw_content) - 1, i, -1):
                    if raw_content[j] == '}':
                        candidate = _try_parse_json(raw_content[i:j+1])
                        if candidate and _is_valid_analysis(candidate):
                            analysis = candidate
                            break
                if analysis is not None:
                    break

    # Strategy 4: Handle the double-wrapped pattern where the entire JSON
    # is inside a JSON string value, e.g. {"{\n  \"summary\": ...}" : ...}
    if analysis is None or not _is_valid_analysis(analysis):
        # Try to find "summary" key and extract the surrounding JSON
        # Look for the pattern: "summary": { ... } and build a valid JSON around it
        summary_idx = raw_content.find('"summary"')
        if summary_idx > 0:
            # Find the opening { before "summary" (the inner JSON start)
            inner_start = raw_content.rfind('{', 0, summary_idx)
            # Find the matching closing }
            depth = 0
            inner_end = -1
            for k in range(inner_start, len(raw_content)):
                if raw_content[k] == '{':
                    depth += 1
                elif raw_content[k] == '}':
                    depth -= 1
                    if depth == 0:
                        inner_end = k
                        break
            if inner_end > inner_start:
                candidate = _try_parse_json(raw_content[inner_start:inner_end + 1])
                if candidate and _is_valid_analysis(candidate):
                    analysis = candidate

    # Strategy 5: Regex extraction as last resort
    if analysis is None or not _is_valid_analysis(analysis):
        summary_text = ""
        # Get the innermost summary text
        summary_matches = re.findall(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_content)
        # Pick the longest match (likely the actual content, not a wrapper key)
        if summary_matches:
            summary_text = max(summary_matches, key=len).replace('\\"', '"').replace("\\n", "\n")

        key_reqs = []
        kr_match = re.search(r'"key_requirements"\s*:\s*\[(.*?)\]', raw_content, re.DOTALL)
        if kr_match:
            raw_list = kr_match.group(1)
            key_reqs = [m.strip().strip('"').replace('\\"', '"') 
                       for m in re.findall(r'"((?:[^"\\]|\\.)*)"', raw_list)]

        actions = []
        act_match = re.search(r'"recommended_actions"\s*:\s*\[(.*?)\]', raw_content, re.DOTALL)
        if act_match:
            raw_list = act_match.group(1)
            actions = [m.strip().strip('"').replace('\\"', '"')
                      for m in re.findall(r'"((?:[^"\\]|\\.)*)"', raw_list)]

        compliance = ""
        comp_match = re.search(r'"compliance_overview"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_content)
        if comp_match:
            compliance = comp_match.group(1).replace('\\"', '"').replace("\\n", "\n")

        risk = ""
        risk_match = re.search(r'"risk_assessment"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_content)
        if risk_match:
            risk = risk_match.group(1).replace('\\"', '"').replace("\\n", "\n")

        # Extract standard_assessments
        assessments = []
        assess_match = re.search(r'"standard_assessments"\s*:\s*\[(.*)\]\s*\}', raw_content, re.DOTALL)
        if assess_match:
            # Extract individual assessment objects
            for obj_match in re.finditer(r'\{[^{}]*"standard_number"[^{}]*\}', assess_match.group(0), re.DOTALL):
                try:
                    a = json.loads(obj_match.group(0))
                    assessments.append(a)
                except (json.JSONDecodeError, ValueError):
                    pass

        analysis = {
            "summary": {
                "summary": summary_text or raw_content[:500],
                "key_requirements": key_reqs,
                "compliance_overview": compliance,
                "risk_assessment": risk,
                "recommended_actions": actions,
            },
            "standard_assessments": assessments,
        }

    # Final normalization — ensure summary is a dict with expected keys
    summary = analysis.get("summary", {})
    if isinstance(summary, str):
        try:
            parsed = json.loads(summary)
            if isinstance(parsed, dict):
                summary = parsed
        except (json.JSONDecodeError, TypeError):
            summary = {
                "summary": summary[:500],
                "key_requirements": [],
                "compliance_overview": "",
                "risk_assessment": "",
                "recommended_actions": [],
            }

    # Normalize assessments
    assessments = analysis.get("standard_assessments", [])
    if isinstance(assessments, str):
        try:
            assessments = json.loads(assessments)
        except (json.JSONDecodeError, TypeError):
            assessments = []

    result = {
        "model_used": model,
        "summary": summary,
        "standard_assessments": assessments,
        "raw_response": raw_content[:2000],
        "tokens_used": tokens_used,
        "latency_ms": elapsed_ms,
        "cached": False,
    }

    # Cache the result
    if use_cache:
        _store_cache(cache_key, text, model, result)

    return result
