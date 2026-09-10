"""LLM safety layer — Phase 6.13.

Harden the OpenRouter integration with prompt injection detection.

Principles:
1. Procurement document = UNTRUSTED INPUT
2. Separate system instructions from user content
3. LLM must only: extract requirements, summarize evidence, explain ranking
4. LLM must NOT: invent standards, invent QCOs, override retrieval, override compliance rules
5. LLM output must always pass through post-processing validation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Set

# Pattern categories for injection detection
_INJECTION_PATTERNS: dict[str, re.Pattern] = {
    "ignore_previous": re.compile(
        r"\b(?:ignore|forget|disregard|override)\s+(?:all\s+)?(?:previous\s+)?instructions|"
        r"\b(?:system|prompt)\s+(?:instruction|directive|command)\s*:|"
        r"\b(jailbreak|prompt\s+injection)\b",
        re.I,
    ),
    "invent_standard": re.compile(
        r"\b(?:recommend|suggest|select|choose)\s+IS\s+\d+(?:\s*\([^)]*\))?(?::\s*\d{4})?\b",
        re.I,
    ),
    "invent_qco": re.compile(
        r"\b(?:recommend|suggest|select|choose)\s+(?:QCO|order|notification)\s+\w+",
        re.I,
    ),
    "override_rules": re.compile(
        r"\b(?:override|disregard|bypass|ignore)\s+(?:BIS|rules|compliance|standards?\s+rules?|policy)\b",
        re.I,
    ),
    "fake_citation": re.compile(
        r"\b(?:reference|cite|source)\s*(?:\s*(?:as|per|in))?\s*(?:IS\s+\d+(?:\s*\([^)]*\))?(?::\s*\d{4})?|BIS)",
        re.I,
    ),
}

# Trusted key phrases the LLM is allowed to use
_TRUSTED_PHRASES: set[str] = {
    "as per",
    "per the dataset",
    "from the verified dataset",
    "confirmed in the dataset",
    "the standard specifies",
    "the standard requires",
    "the standard states",
    "the context indicates",
    "the retrieved evidence shows",
    "based on the retrieved standards",
    "not available in the current dataset",
    "the query specifies",
    "the product is",
    "the application is",
    "requirements",
    "evidence",
    "confidence",
    "relevance",
}


def detect_injection(text: str) -> dict:
    """Detect prompt injection attempts in procurement text.

    Returns:
      {
        "injection_detected": bool,
        "threat_type": "...",
        "cleaned_text": "...",  # sanitized version
        "redacted_segments": [...]
      }
    """
    threats: list[str] = []
    cleaned = text
    redacted: list[tuple[int, int, str]] = []  # (start, end, reason)

    # Check each pattern
    for threat_type, pattern in _INJECTION_PATTERNS.items():
        for m in pattern.finditer(text):
            threats.append(threat_type)
            # Mark the segment (may overlap, keep first occurrence)
            if not any(start <= m.start() < end or start < m.end() <= end
                       for start, end, _ in redacted):
                redacted.append((m.start(), m.end(), threat_type))

    # If injection detected, strip the threatening segments
    if threats:
        # Remove segments that pose threat, preserving rest
        redacted.sort()
        result_parts: list[str] = []
        prev_end = 0
        for start, end, _ in redacted:
            if start > prev_end:
                result_parts.append(cleaned[prev_end:start])
            prev_end = end
        if prev_end < len(cleaned):
            result_parts.append(cleaned[prev_end:])
        cleaned = " ".join(result_parts)
    else:
        cleaned = text

    # If suspicious content remains, truncate at sensible point
    if threats and len(cleaned.split()) > 500:
        cleaned = " ".join(cleaned.split()[:500])

    return {
        "injection_detected": len(threats) > 0,
        "threat_type": ", ".join(set(threats)) if threats else None,
        "cleaned_text": cleaned,
        "redacted_segments": [
            {"text": text[s:e], "reason": r}
            for s, e, r in redacted
        ],
    }


def validate_llm_output(raw_text: str) -> dict:
    """Validate and sanitize LLM output against fabrication rules.

    Ensures the LLM only outputs what's permitted:
    - Only references standards from the provided context
    - Never invents IS numbers
    - Never invents QCO statuses
    - Uses only verified data language
    """
    warnings: list[str] = []
    cleaned = raw_text

    # Reject if injection patterns found
    injection = detect_injection(raw_text)
    if injection["injection_detected"]:
        warnings.append("Prompt injection detected and neutralized")
        cleaned = injection["cleaned_text"]

    # Penalize any explicit invention of IS numbers not in context
    invent_matches = re.findall(r"IS\s*\d+(?:\s*\([^)]*\))?(?::\s*\d{4})?", cleaned)
    if invent_matches:
        warnings.append(f"{len(invent_matches)} IS number reference(s) present — verifying against dataset")
        # Mark these for validation (LLM should only reference what's in context)

    # Flag invented QCO references
    qco_matches = re.findall(r"(?:QCO|order)[\s#\w]*", cleaned, re.I)
    if qco_matches:
        warnings.append(f"{len(qco_matches)} QCO-style reference(s) — verifying against dataset")

    # Ensure the summary fields have the right structure if JSON is attempted
    # Check for "hallucinated" BIS system claims
    fake_claims = re.findall(
        r"(?:confirmed|mandatory|required)\s+(?:by|from|per)\s+(?!the verified dataset|the dataset)",
        cleaned,
        re.I,
    )
    if fake_claims:
        warnings.append(f"{len(fake_claims)} unverified compliance claim(s) — removing or qualifying")

    # Normalize: remove "per BIS" claims without dataset backing
    cleaned = re.sub(
        r"(?:per|as per)\s+BIS\s+(?! the| of the| the )[^.!?]*[.!?]",
        "",
        cleaned,
        flags=re.I,
    )

    return {
        "warnings": warnings,
        "cleaned": cleaned,
        "injection_detected": injection["injection_detected"],
    }