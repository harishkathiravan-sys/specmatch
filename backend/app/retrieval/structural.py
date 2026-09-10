"""Structural requirement extraction — Phase 6.2.

Represents a procurement specification as a structured requirement model:
  product, application, materials, performance_requirements, safety_requirements,
  testing_requirements, certification_requirements, domain, constraints.

Everything is derived deterministically from the specification text.
No fabricated requirements. Confidence per field reflects extraction certainty.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field

from .requirements import extract_deterministic


class StructuredRequirements(BaseModel):
    """Structured interpretation of a procurement specification."""
    product: str = ""
    application: str = ""
    materials: list[str] = Field(default_factory=list)
    performance_requirements: list[str] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list)
    testing_requirements: list[str] = Field(default_factory=list)
    certification_requirements: list[str] = Field(default_factory=list)
    environmental_conditions: list[str] = Field(default_factory=list)
    domain: str = ""
    constraints: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    industry: str = ""
    intended_use: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return self.model_dump()


# ---------------------------------------------------------------
# Deterministic field extractors
# ---------------------------------------------------------------

_PRODUCT_PATTERNS = [
    # "of X" / "for X" phrases at the head of the sentence
    re.compile(r"\b(?:procurement|supply|purchase|acquisition)\s+(?:of|for)\s+([a-zA-Z][a-zA-Z\s\-/]{3,60}?)(?:\s+(?:for|with|having|meeting|as per|suitable|used|which|that))", re.I),
    re.compile(r"\b(?:of|for)\s+([a-zA-Z][a-zA-Z\s\-/]{3,60}?)(?:\s+(?:for|with|having|meeting|as per|suitable|used))", re.I),
]

_APPLICATION_PATTERNS = [
    re.compile(r"\b(?:for|in|used in|suitable for|application in|intended for)\s+([a-zA-Z][a-zA-Z\s\-/]{3,60}?)(?:\s+(?:with|having|meeting|that|which|as per))", re.I),
]

_MATERIAL_TERMS = [
    "mild steel", "stainless steel", "carbon steel", "aluminium", "aluminum",
    "copper", "brass", "bronze", "pvc", "hdpe", "lDPE", "polypropylene",
    "nylon", "polyester", "cotton", "wool", "silk", "rubber", "neoprene",
    "glass", "ceramic", "plastic", "leather", "plywood", "timber", "wood",
    "concrete", "cement", "fibreglass", "glass fiber", "aramid", "kevlar",
    "jute", "felt", "vinyl", "acrylic", "polycarbonate",
]

_PERFORMANCE_TERMS = [
    "tensile strength", "compressive strength", "impact resistance",
    "abrasion resistance", "flame resistance", "fire resistance",
    "fire rating", "water resistance", "waterproof", "weather resistance",
    "uv resistance", "corrosion resistance", "chemical resistance",
    "load bearing", "load capacity", "pressure rating", "burst strength",
    "tear strength", "hardness", "ductility", "elasticity", "stiffness",
    "durability", "wear resistance", "anti-static", "electrostatic",
    "thermal insulation", "sound insulation", "acoustic", "transmission",
    "opacity", "density", "viscosity", "melting point", "flash point",
    "smoke", "low smoke", "self extinguishing", "flammability",
    "low flammability", "strength", "resistance",
]

_SAFETY_TERMS = [
    "safety", "protective", "fire safety", "flame retardant",
    "non-toxic", "halogen free", "smoke density", "toxicity",
    "first aid", "safety footwear", "helmet", "goggles", "gloves",
]

_TESTING_TERMS = [
    "test", "testing", "method of test", "determination", "measurement",
    "inspection", "sampling", "quality control", "verification",
    "calibration", "non-destructive", "ndt", "visual inspection",
]

_CERTIFICATION_TERMS = [
    "qco", "isi", "bis certification", "certification", "licence", "license",
    "mandatory", "compulsory", "legal metrology", "compliance",
    "bureau of indian standards",
]

_ENVIRONMENT_TERMS = [
    "indoor", "outdoor", "marine", "underground", "aircraft", "aerospace",
    "tropical", "coastal", "high temperature", "low temperature",
    "humid", "corrosive environment", "explosive atmosphere", "cleanroom",
]

_DIMENSION_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|g|mg|kN|MPa|bar|psi|°C|micron|µm|litre|l|ml|sq\.?\s*m|m²|m³)\b",
    re.I,
)

_DOMAIN_KEYWORDS: list[tuple[str, list[str]]] = [
    ("textile", ["textile", "fabric", "carpet", "yarn", "fibre", "fiber", "woven", "knitted", "garment", "cloth"]),
    ("construction", ["construction", "building", "cement", "concrete", "aggregate", "brick", "tile", "road", "bridge"]),
    ("electrical", ["electrical", "transformer", "cable", "wire", "switchgear", "voltage", "insulator", "motor"]),
    ("mechanical", ["mechanical", "machinery", "pump", "valve", "bearing", "gear", "hydraulic", "pneumatic", "fastener"]),
    ("chemical", ["chemical", "paint", "coating", "adhesive", "resin", "polymer", "solvent", "pesticide"]),
    ("automotive", ["automotive", "vehicle", "truck", "bus", "car", "two wheeler", "auto"]),
    ("aerospace", ["aircraft", "aerospace", "aviation", "avionics", "airframe", "cabin"]),
    ("medical", ["medical", "pharmaceutical", "clinical", "surgical", "ophthalmic", "hospital"]),
    ("food", ["food", "dairy", "beverage", "spice", "oil", "grain", "packaging"]),
    ("defence", ["defence", "defense", "military", "ammunition", "armament"]),
    ("packaging", ["packaging", "carton", "corrugated", "flexible packaging", "container"]),
    ("environment", ["environment", "water quality", "air quality", "emission", "effluent"]),
]

_INDUSTRY_KEYWORDS = [
    ("mining", ["mining", "mine", "mineral"]),
    ("power", ["power", "transmission line", "substation", "grid"]),
    ("railways", ["railway", "rail", "track", "rolling stock", "locomotive"]),
    ("defence", ["defence", "defense", "military"]),
    ("pharmaceutical", ["pharma", "drug", "medicine", "injection"]),
    ("aerospace", ["aircraft", "aviation", "aerospace"]),
    ("automotive", ["automotive", "vehicle", "auto"]),
]

_CONSTRAINT_PATTERNS = [
    re.compile(r"\b(?:must|shall|required to|should)\s+([a-zA-Z][a-zA-Z\s\-/,]{5,80}?)(?:\.|,|\band\b|\bwith\b)", re.I),
    re.compile(r"\b(?:not exceeding|not less than|maximum|minimum|up to)\s+([a-zA-Z0-9][a-zA-Z0-9\s\-/.%°]{2,40})", re.I),
]


def _extract_field_with_patterns(text: str, patterns: list[re.Pattern]) -> str:
    for pat in patterns:
        m = pat.search(text)
        if m:
            val = m.group(1).strip()
            # Trim trailing filler
            val = re.sub(r"\s+(?:and|with|that|which|having)\s*$", "", val)
            if len(val) >= 3:
                return val
    return ""


def _collect_matches(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    found: list[str] = []
    for term in terms:
        if term.lower() in low and term.lower() not in found:
            found.append(term.lower())
    return found


def _extract_constraints(text: str) -> list[str]:
    constraints: list[str] = []
    for pat in _CONSTRAINT_PATTERNS:
        for m in pat.finditer(text):
            c = m.group(1).strip()
            if len(c) >= 4 and c not in constraints:
                constraints.append(c[:120])
    return constraints[:8]


def extract_structured(text: str) -> StructuredRequirements:
    """Deterministic structural requirement extraction."""
    low = text.lower()

    product = _extract_field_with_patterns(text, _PRODUCT_PATTERNS)
    application = _extract_field_with_patterns(text, _APPLICATION_PATTERNS)
    materials = _collect_matches(text, _MATERIAL_TERMS)
    performance = _collect_matches(text, _PERFORMANCE_TERMS)
    safety = _collect_matches(text, _SAFETY_TERMS)
    testing = _collect_matches(text, _TESTING_TERMS)
    certification = _collect_matches(text, _CERTIFICATION_TERMS)
    environmental = _collect_matches(text, _ENVIRONMENT_TERMS)
    dimensions = [m.group(0) for m in _DIMENSION_RE.finditer(text)][:6]

    # Domain
    domain = ""
    for name, kws in _DOMAIN_KEYWORDS:
        if any(kw in low for kw in kws):
            domain = name
            break

    # Industry
    industry = ""
    for name, kws in _INDUSTRY_KEYWORDS:
        if any(kw in low for kw in kws):
            industry = name
            break

    constraints = _extract_constraints(text)

    # Intended use — fall to application or product phrase
    intended_use = application or product

    # Confidence: more structured signals found = higher confidence
    signal_count = sum([
        bool(product), bool(application), bool(materials), bool(performance),
        bool(safety), bool(testing), bool(certification), bool(environmental),
        bool(dimensions), bool(domain), bool(constraints),
    ])
    confidence = round(min(0.95, 0.35 + 0.05 * signal_count), 3)

    return StructuredRequirements(
        product=product,
        application=application,
        materials=materials,
        performance_requirements=performance,
        safety_requirements=safety,
        testing_requirements=testing,
        certification_requirements=certification,
        environmental_conditions=environmental,
        domain=domain,
        constraints=constraints,
        dimensions=dimensions,
        industry=industry,
        intended_use=intended_use,
        confidence=confidence,
    )


# ---------------------------------------------------------------
# Requirement coverage computation — 6.2
# ---------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _token_overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta)


def compute_requirement_coverage(
    structured: StructuredRequirements,
    standard: dict,
) -> dict:
    """Compute requirement coverage for a candidate standard.

    Returns:
      {
        "score": 0-1,
        "matched": [...],
        "unmatched": [...],
        "details": {...}
      }

    A standard is only penalized for requirements that are clearly relevant
    to its domain. Requirements outside the domain are excluded.
    """
    matched: list[str] = []
    unmatched: list[str] = []
    details: dict = {}

    title = standard.get("title", "")
    keywords = standard.get("derived_keywords", "")
    searchable = f"{title} {keywords}"
    search_tokens = _tokens(searchable)

    # 1. Product match
    if structured.product:
        p_score = _token_overlap(structured.product, title)
        if p_score >= 0.3 or _token_overlap(structured.product, keywords) >= 0.3:
            matched.append(f"product:{structured.product}")
            details["product"] = "matched"
        else:
            unmatched.append(f"product:{structured.product}")
            details["product"] = "unmatched"

    # 2. Application match
    if structured.application:
        a_score = _token_overlap(structured.application, title)
        if a_score >= 0.4 or structured.application.lower() in searchable.lower():
            matched.append(f"application:{structured.application}")
            details["application"] = "matched"
        else:
            unmatched.append(f"application:{structured.application}")
            details["application"] = "unmatched"

    # 3. Material match — standard only penalized if materials exist AND domain matches
    if structured.materials:
        material_hits = [m for m in structured.materials if m.lower() in searchable.lower()]
        if material_hits:
            matched.extend(f"material:{m}" for m in material_hits)
            details["materials"] = "matched"
        elif structured.domain and _domain_relevant(structured.domain, title):
            unmatched.extend(f"material:{m}" for m in structured.materials)
            details["materials"] = "unmatched"
        else:
            details["materials"] = "not_applicable"

    # 4. Performance requirements
    if structured.performance_requirements:
        perf_hits = [p for p in structured.performance_requirements if p.lower() in searchable.lower()]
        if perf_hits:
            matched.extend(f"performance:{p}" for p in perf_hits)
            details["performance"] = "matched"
        else:
            unmatched.extend(f"performance:{p}" for p in structured.performance_requirements)
            details["performance"] = "unmatched"

    # 5. Safety requirements
    if structured.safety_requirements:
        safety_hits = [s for s in structured.safety_requirements if s.lower() in searchable.lower()]
        if safety_hits:
            matched.extend(f"safety:{s}" for s in safety_hits)
            details["safety"] = "matched"
        else:
            unmatched.extend(f"safety:{s}" for s in structured.safety_requirements)
            details["safety"] = "unmatched"

    # 6. Testing requirements
    if structured.testing_requirements:
        test_hits = [t for t in structured.testing_requirements if t.lower() in searchable.lower()]
        if test_hits:
            matched.extend(f"testing:{t}" for t in test_hits)
            details["testing"] = "matched"
        else:
            unmatched.extend(f"testing:{t}" for t in structured.testing_requirements)
            details["testing"] = "unmatched"

    # 7. Certification requirements
    if structured.certification_requirements:
        cert_hits = [c for c in structured.certification_requirements if c.lower() in searchable.lower()]
        if cert_hits:
            matched.extend(f"certification:{c}" for c in cert_hits)
            details["certification"] = "matched"
        else:
            unmatched.extend(f"certification:{c}" for c in structured.certification_requirements)
            details["certification"] = "unmatched"

    # 8. Environmental conditions
    if structured.environmental_conditions:
        env_hits = [e for e in structured.environmental_conditions if e.lower() in searchable.lower()]
        if env_hits:
            matched.extend(f"environment:{e}" for e in env_hits)
            details["environment"] = "matched"
        else:
            unmatched.extend(f"environment:{e}" for e in structured.environmental_conditions)
            details["environment"] = "unmatched"

    # 9. Dimensions
    if structured.dimensions:
        # Dimensions rarely literally appear in title — treat as neutral unless domain matches
        details["dimensions"] = "informational"

    # Compute score: matched / (matched + relevant_unmatched)
    total_relevant = len(matched) + len(unmatched)
    score = round(len(matched) / total_relevant, 4) if total_relevant > 0 else 0.0

    return {
        "score": score,
        "matched": matched[:20],
        "unmatched": unmatched[:20],
        "details": details,
    }


def _domain_relevant(domain: str, title: str) -> bool:
    """Heuristic: is the standard's title in the same domain as requirement?"""
    domain_tokens: dict[str, set[str]] = {
        "textile": {"textile", "fabric", "carpet", "yarn", "woven", "cloth", "garment"},
        "construction": {"construction", "cement", "concrete", "building", "brick", "tile"},
        "electrical": {"electrical", "transformer", "cable", "wire", "switchgear"},
        "mechanical": {"mechanical", "pump", "valve", "bearing", "gear", "fastener"},
        "chemical": {"chemical", "paint", "coating", "adhesive", "resin"},
        "aerospace": {"aircraft", "aerospace", "aviation", "cabin"},
        "automotive": {"automotive", "vehicle", "truck", "bus"},
    }
    toks = domain_tokens.get(domain, set())
    title_toks = _tokens(title)
    return bool(toks & title_toks)