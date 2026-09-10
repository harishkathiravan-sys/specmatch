"""Contradiction / mismatch detection — Phase 6.3.

Detects when a candidate standard is lexically similar but technically wrong:
  - wrong product category
  - wrong application
  - wrong industry
  - incompatible material
  - incompatible use case

Contradictions reduce applicability but the standard is not removed —
instead it is ranked lower with an explicit reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .structural import StructuredRequirements


# ---------------------------------------------------------------
# Domain vocabulary — used to detect contradictions
# ---------------------------------------------------------------

_DOMAIN_SIGNALS: dict[str, set[str]] = {
    "textile": {"textile", "fabric", "carpet", "yarn", "fibre", "fiber", "woven", "knitted", "cloth", "garment", "curtain", "upholstery", "tapestry"},
    "construction": {"construction", "cement", "concrete", "brick", "tile", "building", "road", "bridge", "aggregate", "mortar", "plaster"},
    "electrical": {"electrical", "transformer", "cable", "wire", "switchgear", "voltage", "insulator", "motor", "generator", "capacitor", "relay"},
    "electronics": {"electronic", "circuit", "semiconductor", "diode", "transistor", "resistor", "pcb", "integrated circuit"},
    "mechanical": {"mechanical", "machinery", "pump", "valve", "bearing", "gear", "hydraulic", "pneumatic", "fastener", "bolt", "nut", "screw"},
    "chemical": {"chemical", "paint", "coating", "adhesive", "resin", "polymer", "solvent", "pesticide", "fertilizer", "acid"},
    "aerospace": {"aircraft", "aerospace", "aviation", "cabin", "airframe", "aero", "flight"},
    "automotive": {"automotive", "vehicle", "truck", "bus", "car", "two wheeler", "tractor", "chassis"},
    "medical": {"medical", "pharmaceutical", "clinical", "surgical", "ophthalmic", "hospital", "injection", "syringe", "cannula"},
    "food": {"food", "dairy", "beverage", "spice", "oil", "grain", "packaging", "edible"},
    "defence": {"defence", "defense", "military", "ammunition", "armament", "ballistic"},
    "marine": {"marine", "ship", "boat", "vessel", "offshore", "naval"},
    "packaging": {"packaging", "carton", "corrugated", "flexible packaging", "container", "bottle"},
    "fire_safety": {"fire", "extinguisher", "sprinkler", "fire hose", "firefighting", "fire alarm"},
    "electrical_cables": {"cable", "wire", "conductor", "insulated"},
}

# Token-level contradiction signals: these words in a query vs. standard title
_APPLICATION_COUNTERS = {
    "aircraft": {"residential", "domestic", "home", "household"},
    "marine": {"terrestrial", "land", "indoor"},
    "automotive": {"aircraft", "residential"},
    "industrial": {"residential", "domestic"},
    "medical": {"industrial", "automotive"},
}

# Products that often confuse but are technically different
_CONFUSING_PAIRS: list[tuple[str, str]] = [
    # (application/product hint, conflicting standard product hint)
    ("aircraft", "residential"),
    ("aircraft", "domestic"),
    ("woven carpet", "non-woven"),
    ("floor covering", "wall covering"),
    ("extinguisher", "hose"),
    ("sprinkler", "nozzle"),
]


@dataclass
class Contradiction:
    """A detected mismatch between query and candidate standard."""
    type: str          # product_category, application, industry, material, use_case
    reason: str        # human-readable explanation
    severity: str      # high, medium, low
    penalty: float     # 0-1 penalty applied to final score

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "reason": self.reason,
            "severity": self.severity,
            "penalty": self.penalty,
        }


def _domain_of(text: str) -> Optional[str]:
    """Return the dominant domain for a text, else None."""
    low = text.lower()
    best_domain = None
    best_count = 0
    for domain, signals in _DOMAIN_SIGNALS.items():
        count = sum(1 for s in signals if s in low)
        if count > best_count and count >= 2:
            best_domain = domain
            best_count = count
    return best_domain


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def detect_contradictions(
    query: str,
    structured: StructuredRequirements,
    standard: dict,
) -> list[Contradiction]:
    """Detect mismatches between the query and a candidate standard.

    Returns a list of Contradiction objects; empty if none found.
    """
    contradictions: list[Contradiction] = []
    query_low = query.lower()
    title = standard.get("title", "")
    title_low = title.lower()
    q_tokens = _tokens(query)
    t_tokens = _tokens(title)

    # Skip if query has no meaningful terms
    if not q_tokens or not t_tokens:
        return contradictions

    # ── 1. Domain mismatch ──────────────────────────────────────────────
    q_domain = structured.domain or _domain_of(query)
    t_domain = _domain_of(title)

    if q_domain and t_domain and q_domain != t_domain:
        # Look for overlap in signals to avoid false positives
        q_signals = _DOMAIN_SIGNALS.get(q_domain, set())
        t_signals = _DOMAIN_SIGNALS.get(t_domain, set())
        # Only flag if domains are truly distinct (no overlapping vocabulary)
        if not (q_signals & t_signals):
            contradictions.append(Contradiction(
                type="industry",
                reason=(
                    f"The query is in the {q_domain} domain, but the candidate "
                    f"is in the {t_domain} domain."
                ),
                severity="high",
                penalty=0.35,
            ))

    # ── 2. Application mismatch ─────────────────────────────────────────
    for app_word, counter_words in _APPLICATION_COUNTERS.items():
        if app_word in query_low:
            found = [c for c in counter_words if c in title_low]
            if found:
                contradictions.append(Contradiction(
                    type="application",
                    reason=(
                        f"The query targets {app_word} applications, but the "
                        f"candidate targets {', '.join(found)} use."
                    ),
                    severity="high",
                    penalty=0.30,
                ))

    # ── 3. Product-type confusion pairs ─────────────────────────────────
    for query_hint, std_hint in _CONFUSING_PAIRS:
        if query_hint in query_low and std_hint in title_low:
            contradictions.append(Contradiction(
                type="product_category",
                reason=(
                    f"The candidate relates to {std_hint} products while the "
                    f"query specifies {query_hint} products."
                ),
                severity="medium",
                penalty=0.20,
            ))

    # ── 4. Material mismatch (when materials are specified and standard names another material) ──
    if structured.materials:
        std_materials = [m for m in structured.materials if m in title_low]
        # If the standard is in the same broad domain but does NOT mention the
        # required materials, only flag as medium contradiction when the material
        # is core to the product (e.g., "woven carpet" - material matters)
        if structured.product and not std_materials:
            # Check for a direct conflicting material mention
            for alt_mat in ["cotton", "wool", "nylon", "polyester", "steel", "plastic"]:
                if alt_mat in title_low and alt_mat not in structured.materials:
                    contradictions.append(Contradiction(
                        type="material",
                        reason=(
                            f"The candidate is made with {alt_mat}, but the "
                            f"query specifies {', '.join(structured.materials)}."
                        ),
                        severity="medium",
                        penalty=0.15,
                    ))
                    break

    # ── 5. Use-case incompatibility ─────────────────────────────────────
    if structured.application and structured.intended_use:
        # The standard title should reflect the intended use when it's in the
        # same domain. If the standard is in a different sector, flag it.
        app_domain = _domain_of(structured.application)
        if app_domain and t_domain and app_domain != t_domain:
            contradictions.append(Contradiction(
                type="use_case",
                reason=(
                    f"Suitable for {app_domain} use; candidate is a {t_domain} product."
                ),
                severity="low",
                penalty=0.10,
            ))

    # Deduplicate identical reasons
    seen: set[str] = set()
    unique: list[Contradiction] = []
    for c in contradictions:
        if c.reason not in seen:
            seen.add(c.reason)
            unique.append(c)
    return unique


def contradiction_penalty(contradictions: list[Contradiction]) -> float:
    """Combine penalties from all contradictions, capped at 0.6."""
    if not contradictions:
        return 0.0
    total = sum(c.penalty for c in contradictions)
    return round(min(0.6, total), 4)