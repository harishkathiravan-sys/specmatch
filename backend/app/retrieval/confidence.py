"""Confidence assessment — separate from relevance score.

Confidence indicates how reliable the recommendation signal is,
NOT whether the standard is legally/compliance-applicable.

Three dimensions:
  - relevance_score: How well the standard matches the query (0-1)
  - confidence: Assessment of recommendation reliability (high/medium/low)
  - compliance_status: Whether compliance is validated (NOT validated by this system)

Confidence rules:
  High:    Multiple retrieval methods agree, strong evidence, clear title match
  Medium:  Some uncertainty, partial evidence, moderate signal strength
  Low:     Weak evidence, single retrieval method, or disagreement between signals
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ConfidenceAssessment:
    """Confidence assessment for a recommendation."""
    relevance_score: float           # 0.0 - 1.0
    confidence: str                  # "high", "medium", "low"
    confidence_reason: str           # Human-readable explanation
    compliance_status: str           # "not_validated" (always, by design)
    compliance_display: str          # "Not validated"

    def to_dict(self) -> dict:
        return {
            "relevance_score": round(self.relevance_score, 4),
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "compliance_status": self.compliance_status,
            "compliance_display": self.compliance_display,
        }


def assess_confidence(
    relevance_score: float,
    lexical_score: Optional[float] = None,
    semantic_score: Optional[float] = None,
    metadata_score: Optional[float] = None,
    reranker_score: Optional[float] = None,
    evidence_count: int = 0,
    retrieval_methods: Optional[list[str]] = None,
    title_match: bool = False,
) -> ConfidenceAssessment:
    """Assess recommendation confidence based on multiple signals.

    Considered factors:
    1. Agreement between retrieval methods
    2. Strength of relevance score
    3. Title match presence
    4. Evidence availability
    5. Reranker confirmation

    This does NOT determine compliance or legal applicability.
    """
    methods = retrieval_methods or []

    # Score components
    score_signals = 0
    max_signals = 5

    # 1. Method agreement (found by 2+ methods = strong signal)
    if len(methods) >= 3:
        score_signals += 1.0
    elif len(methods) >= 2:
        score_signals += 0.7
    elif len(methods) >= 1:
        score_signals += 0.3

    # 2. Relevance score strength
    if relevance_score >= 0.8:
        score_signals += 1.0
    elif relevance_score >= 0.5:
        score_signals += 0.6
    elif relevance_score >= 0.3:
        score_signals += 0.3

    # 3. Title match
    if title_match:
        score_signals += 1.0

    # 4. Evidence availability
    if evidence_count >= 3:
        score_signals += 1.0
    elif evidence_count >= 2:
        score_signals += 0.6
    elif evidence_count >= 1:
        score_signals += 0.3

    # 5. Reranker confirmation
    if reranker_score is not None and reranker_score >= 0.5:
        score_signals += 1.0
    elif reranker_score is not None and reranker_score >= 0.3:
        score_signals += 0.5

    # Normalize to 0-1
    normalized = score_signals / max_signals

    # Determine confidence level
    if normalized >= 0.65:
        confidence = "high"
        reason = "Strong independent retrieval agreement and clear evidence."
    elif normalized >= 0.40:
        confidence = "medium"
        reason = "Relevant candidate but some uncertainty exists."
    else:
        confidence = "low"
        reason = "Weak evidence or disagreement between retrieval signals."

    # Refine reason based on specific conditions
    if title_match and confidence == "high":
        reason = "Title directly matches the query. Multiple retrieval signals agree."
    elif len(methods) >= 2 and evidence_count >= 2:
        reason = f"Found by {len(methods)} retrieval methods with {evidence_count} evidence signals."
    elif len(methods) < 2:
        reason = f"Single retrieval method ({methods[0] if methods else 'unknown'}). Limited independent verification."

    return ConfidenceAssessment(
        relevance_score=round(relevance_score, 4),
        confidence=confidence,
        confidence_reason=reason,
        compliance_status="not_validated",
        compliance_display="Not validated",
    )
