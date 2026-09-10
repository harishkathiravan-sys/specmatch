"""Query normalization — deterministic, no LLM.

Produces a structured NormalizedQuery used by all retrieval strategies.

Preserves IS standard identifiers; removes stop-words/punctuation;
extracts technical phrases and product/application hints.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# Stop words to drop for normalized_query (procurement filler)
_STOP = {
    "the","a","an","and","or","of","for","in","to","is","by","on","at","with","from",
    "procurement","supply","installation","testing","suitable","shall","should","would","could",
    "must","will","are","be","been","being","have","has","had","this","that","which","what",
    "requirement","requirements","specification","specifications","applicable","requirements",
    "standard","standards","material","materials","product","products","service","services",
}

# Known domain phrases — used for phrase-aware tokenization
# Curated from BIS titles + procurement language (not fabricated)
_KNOWN_PHRASES = [
    "woven carpet","textile floor covering","aircraft interior","aircraft woven carpet",
    "fibre rope","steel wire rope","power transformer","distribution transformer",
    "concrete admixture","cement concrete","mild steel","stainless steel",
    "pvc pipe","hdpe pipe","gi pipe","fire extinguisher","fire hose",
    "safety helmet","safety footwear","protective clothing",
    "laboratory glassware","medical device","pharmaceutical",
]

# Regex for IS identifiers — preserved verbatim
_IS_RE = re.compile(r"\bIS\s*\d+(?:\s*\(?\s*Part\s*\d+[^\)]*\)?)?(?:\s*:\s*\d{4})?\b", re.IGNORECASE)
# Year suffix like :2026
_YEAR_RE = re.compile(r":\d{4}\b")

@dataclass
class NormalizedQuery:
    raw_query: str
    normalized_query: str
    technical_terms: list[str] = field(default_factory=list)
    product_terms: list[str] = field(default_factory=list)
    application_terms: list[str] = field(default_factory=list)
    is_identifiers: list[str] = field(default_factory=list)
    # For backward compat / logging
    query_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "technical_terms": self.technical_terms,
            "product_terms": self.product_terms,
            "application_terms": self.application_terms,
            "is_identifiers": self.is_identifiers,
        }

def _clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _strip_punctuation_keep_slash(s: str) -> str:
    # Keep alphanum, space, slash, hyphen for compound terms
    return re.sub(r"[^a-zA-Z0-9\s/\-]", " ", s)

def normalize(raw: str) -> NormalizedQuery:
    """Deterministic normalization."""
    if not raw or not raw.strip():
        return NormalizedQuery(raw_query=raw or "", normalized_query="", technical_terms=[], product_terms=[], application_terms=[], is_identifiers=[], query_terms=[])

    q = raw.strip()
    # Extract IS identifiers first
    is_ids = [m.group(0).strip() for m in _IS_RE.finditer(q)]
    # Remove IS ids from the text for term extraction (keep them separately)
    q_no_is = _IS_RE.sub(" ", q)

    # Lowercase for analysis, but preserve original for display
    low = q_no_is.lower()

    # Detect known phrases (case-insensitive) before stripping
    found_phrases: list[str] = []
    for phrase in _KNOWN_PHRASES:
        if phrase.lower() in low:
            found_phrases.append(phrase.lower())

    # Clean punctuation and normalize whitespace
    cleaned = _strip_punctuation_keep_slash(low)
    cleaned = _clean_whitespace(cleaned)

    tokens = [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", cleaned) if t]
    # Remove stop words and very short tokens
    filtered = [t for t in tokens if len(t) > 2 and t not in _STOP]

    # Deduplicate preserving order
    seen = set()
    query_terms: list[str] = []
    for t in filtered:
        if t not in seen:
            seen.add(t)
            query_terms.append(t)

    # Prepend multi-word phrases that were found
    technical_terms: list[str] = []
    # Add found known phrases as technical terms
    for p in found_phrases:
        if p not in technical_terms:
            technical_terms.append(p)
    # Add significant single terms as technical_terms (top 8)
    for t in query_terms[:8]:
        if t not in technical_terms:
            technical_terms.append(t)

    # Heuristic product vs application split
    product_hints = {"carpet","fabric","textile","rope","pipe","cable","wire","transformer","concrete","steel","aluminium","aluminum","helmet","footwear","glassware","chemical","paint","coating","adhesive","resin","machinery","equipment","valve","pump","bearing","gear","tile","brick","cement","plywood","timber","door","window"}
    application_hints = {"aircraft","interior","building","construction","road","bridge","railway","airport","hospital","laboratory","mining","power","electrical","civil","mechanical","safety"}

    product_terms = [t for t in query_terms if any(ph in t for ph in product_hints) or t in product_hints]
    # Also promote multi-word product phrases
    for p in found_phrases:
        if any(w in p for w in product_hints) and p not in product_terms:
            product_terms.append(p)

    application_terms = [t for t in query_terms if t in application_hints]
    for p in found_phrases:
        if "aircraft interior" in p and p not in application_terms:
            application_terms.append(p)

    normalized_query = " ".join(query_terms)
    # If no terms but we have IS id, use that
    if not normalized_query and is_ids:
        normalized_query = is_ids[0]

    return NormalizedQuery(
        raw_query=raw,
        normalized_query=normalized_query,
        technical_terms=technical_terms,
        product_terms=product_terms,
        application_terms=application_terms,
        is_identifiers=is_ids,
        query_terms=query_terms,
    )

# Backward-compat helper used by old code
def normalize_query_text(raw: str) -> str:
    return normalize(raw).normalized_query
