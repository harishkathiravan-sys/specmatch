"""Evidence extraction — generate evidence items for each recommendation.

Every recommendation must have evidence derived from actual data.
No fabricated or hallucinated evidence.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvidenceItem:
    """A single piece of evidence for why a standard was recommended."""
    type: str          # title_match, keyword_match, metadata_match, retrieval_signal, etc.
    text: str          # The evidence text
    source: str        # Where it came from (standard.title, derived_keywords, etc.)
    strength: str = "moderate"  # strong, moderate, weak

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "text": self.text,
            "source": self.source,
            "strength": self.strength,
        }


def extract_evidence(
    query: str,
    standard: dict,
    matching_terms: list[str],
    retrieval_methods: list[str],
) -> list[EvidenceItem]:
    """Extract evidence for why this standard matches the query.

    All evidence is grounded in actual data — title, keywords, metadata.
    Returns empty list if no meaningful evidence is found.
    """
    evidence: list[EvidenceItem] = []
    query_lower = query.lower()
    title = standard.get("title", "")
    title_lower = title.lower()
    keywords = standard.get("derived_keywords") or ""
    kw_lower = keywords.lower()
    sector = standard.get("sector") or ""
    product_category = standard.get("product_category") or ""

    # 1. Title match evidence
    query_tokens = set(re.findall(r"[a-z0-9]{3,}", query_lower))
    title_tokens = set(re.findall(r"[a-z0-9]{3,}", title_lower))

    # Exact phrase in title
    if len(query_lower) > 5 and query_lower in title_lower:
        evidence.append(EvidenceItem(
            type="title_match",
            text=f"Direct phrase match in title",
            source="standard.title",
            strength="strong",
        ))
    else:
        # Token-level title matches
        title_overlap = query_tokens & title_tokens
        if title_overlap:
            matched_words = sorted(title_overlap)[:5]
            evidence.append(EvidenceItem(
                type="title_match",
                text=f"Title contains: {', '.join(matched_words)}",
                source="standard.title",
                strength="strong" if len(title_overlap) >= 3 else "moderate",
            ))

    # 2. Keyword match evidence
    kw_tokens = set(re.findall(r"[a-z0-9]{3,}", kw_lower))
    kw_overlap = query_tokens & kw_tokens
    if kw_overlap:
        matched_kw = sorted(kw_overlap)[:5]
        evidence.append(EvidenceItem(
            type="keyword_match",
            text=f"Keywords match: {', '.join(matched_kw)}",
            source="derived_keywords",
            strength="strong" if len(kw_overlap) >= 3 else "moderate",
        ))

    # 3. Matching terms from retrieval (from lexical search)
    if matching_terms:
        evidence.append(EvidenceItem(
            type="retrieval_match",
            text=f"Retrieved via terms: {', '.join(matching_terms[:5])}",
            source="retrieval",
            strength="moderate",
        ))

    # 4. Metadata matches
    for term in (standard.get("matching_terms") or [])[:3]:
        if term in query_lower or term in title_lower:
            # Determine which metadata field matched
            term_lower = term.lower()
            if term_lower in (sector or "").lower():
                evidence.append(EvidenceItem(
                    type="metadata_match",
                    text=f"Sector match: {sector}",
                    source="standard.sector",
                    strength="weak",
                ))
            elif term_lower in (product_category or "").lower():
                evidence.append(EvidenceItem(
                    type="metadata_match",
                    text=f"Product category: {product_category}",
                    source="standard.product_category",
                    strength="moderate",
                ))

    # 5. Retrieval signal evidence
    if len(retrieval_methods) > 1:
        method_labels = {
            "lexical": "lexical search",
            "semantic": "semantic similarity",
            "metadata": "metadata matching",
        }
        labels = [method_labels.get(m, m) for m in retrieval_methods]
        evidence.append(EvidenceItem(
            type="retrieval_signal",
            text=f"Found by: {', '.join(labels)}",
            source="retrieval_pipeline",
            strength="strong" if len(retrieval_methods) >= 2 else "moderate",
        ))

    # Sort by strength
    strength_order = {"strong": 0, "moderate": 1, "weak": 2}
    evidence.sort(key=lambda e: strength_order.get(e.strength, 3))

    return evidence


def format_evidence_summary(evidence: list[EvidenceItem]) -> str:
    """Generate a human-readable evidence summary."""
    if not evidence:
        return "Limited evidence available for this recommendation."

    parts = []
    for e in evidence[:5]:
        parts.append(f"[{e.type}] {e.text}")

    return " | ".join(parts)
