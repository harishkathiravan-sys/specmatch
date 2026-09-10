"""Structured requirement extraction — deterministic + optional LLM.

Produces typed requirements with confidence; never hallucinates standard IDs.
LLM is optional and validated via Pydantic; falls back to deterministic parser.
"""

import re
from dataclasses import dataclass, field
from typing import Literal, Optional
from pydantic import BaseModel, Field

RequirementType = Literal[
    "product","material","application","performance","dimension","environment","industry","process","testing","certification","other","unknown"
]

class Requirement(BaseModel):
    text: str = Field(..., min_length=2, max_length=500)
    type: RequirementType = "unknown"
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)

class RequirementsResult(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

# --- deterministic extraction ---

_TYPE_PATTERNS: list[tuple[re.Pattern, RequirementType]] = [
    (re.compile(r"\b(IS\s*\d+[^\n]*|specification|standard)\b", re.I), "product"),
    (re.compile(r"\b(mild steel|stainless steel|aluminium|aluminum|pvc|hdpe|gi\b|nylon|polyester|cotton|wool|silk|rubber|plastic|glass|ceramic)\b", re.I), "material"),
    (re.compile(r"\b(for|in|used in|application|suitable for)\s+[a-z ]{3,40}", re.I), "application"),
    (re.compile(r"\b\d+(?:\.\d+)?\s*(mm|cm|m\b|kg|g\b|kN|MPa|bar|psi|°C|micron|litre|L\b)", re.I), "dimension"),
    (re.compile(r"\b(tensile|compressive|impact|hardness|abrasion|resistance|strength|durability|fire rating|load|capacity)\b", re.I), "performance"),
    (re.compile(r"\b(indoor|outdoor|underground|marine|aircraft|building|road|bridge|railway|hospital|laboratory)\b", re.I), "environment"),
    (re.compile(r"\b(test|testing|method of test|determination|measurement|inspection|sampling)\b", re.I), "testing"),
    (re.compile(r"\b(QCO|ISI|certification|BIS|licence|license|compliance)\b", re.I), "certification"),
    (re.compile(r"\b(manufactur|process|fabricat|woven|knitted|extruded|cast|forged|welded)\b", re.I), "process"),
]

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "electrical": ["electrical","power","voltage","cable","wire","transformer","switchgear"],
    "mechanical": ["mechanical","machinery","equipment","hydraulic","pump","valve","bearing","gear"],
    "civil": ["construction","concrete","steel","building","road","bridge","cement","aggregate","brick","tile"],
    "chemical": ["chemical","paint","coating","adhesive","resin","pesticide","fertilizer"],
    "textile": ["textile","fabric","cloth","garment","carpet","yarn","fibre","fibre rope","woven","knitted"],
    "electronic": ["electronic","semiconductor","circuit","digital","information technology"],
    "safety": ["safety","protection","helmet","fire","extinguisher","hose","footwear"],
    "medical": ["medical","pharmaceutical","health","clinical","surgical","ophthalmic"],
    "food": ["food","agriculture","dairy","beverage","spice","oil"],
    "environmental": ["environment","water","air","waste","pollution"],
}

_STOP_WORDS = {
    "that","this","with","from","have","been","were","will","shall","should","would","could","might","must","about",
    "such","than","then","also","only","into","over","more","when","what","which","where","there","their","these",
    "those","some","other","each","every","both","most","requirements","specification","compliance","procurement",
    "supply","installation","testing","suitable","applicable","standard","material","product","service",
}

def _classify(text: str) -> RequirementType:
    low = text.lower()
    for pat, typ in _TYPE_PATTERNS:
        if pat.search(low):
            return typ
    # Fallback heuristic
    if any(w in low for w in ("carpet","fabric","rope","pipe","cable","transformer","concrete","steel","chemical")):
        return "product"
    return "other"

def _extract_keywords(text: str) -> list[str]:
    low = text.lower()
    phrases = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", text)
    words = re.findall(r"[a-zA-Z]{4,}", low)
    kws: set[str] = set()
    for p in phrases[:10]:
        p = p.strip().lower()
        if len(p) > 3 and p not in _STOP_WORDS:
            kws.add(p)
    for w in words:
        if w not in _STOP_WORDS:
            kws.add(w)
    return sorted(kws)[:30]

def _identify_categories(text: str) -> list[str]:
    low = text.lower()
    cats: list[str] = []
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in low for kw in kws):
            cats.append(cat)
    return cats

def extract_deterministic(text: str) -> RequirementsResult:
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n\d+[.)]\s*|\s*;\s*", text)
    reqs: list[Requirement] = []
    for p in parts:
        p = p.strip()
        if len(p) < 10:
            continue
        # Further split long clauses on commas / and
        if len(p) > 160:
            clauses = re.split(r",\s*|\s+and\s+", p)
            for c in clauses:
                c = c.strip()
                if len(c) < 12:
                    continue
                typ = _classify(c)
                # Confidence: product/material higher if keyword-rich
                conf = 0.85 if typ in ("product","material") and len(c.split()) >= 3 else 0.72 if typ != "unknown" else 0.6
                reqs.append(Requirement(text=c[:300], type=typ, confidence=conf))
                if len(reqs) >= 20:
                    break
        else:
            typ = _classify(p)
            conf = 0.88 if typ in ("product","material","testing") else 0.7 if typ != "unknown" else 0.58
            reqs.append(Requirement(text=p[:300], type=typ, confidence=conf))
        if len(reqs) >= 20:
            break
    # If still empty, treat whole text as one requirement
    if not reqs and text.strip():
        reqs.append(Requirement(text=text.strip()[:300], type=_classify(text[:200]), confidence=0.62))

    return RequirementsResult(
        requirements=reqs[:20],
        keywords=_extract_keywords(text),
        categories=_identify_categories(text),
    )

# --- LLM provider abstraction (optional) ---

class LLMProvider:
    """Abstract LLM for requirement extraction / query expansion / explanations."""
    def extract_requirements(self, text: str) -> list[Requirement]:
        raise NotImplementedError
    def expand_query(self, text: str) -> list[str]:
        raise NotImplementedError
    def generate_explanation(self, query: str, standard: dict) -> str:
        raise NotImplementedError

def extract_requirements(text: str, llm: Optional[LLMProvider] = None) -> RequirementsResult:
    """Main entry — tries LLM once, validates, falls back to deterministic."""
    if llm is not None:
        try:
            llm_reqs = llm.extract_requirements(text)
            # Validate each
            validated: list[Requirement] = []
            for r in llm_reqs:
                # Re-validate via Pydantic
                validated.append(Requirement.model_validate(r.model_dump() if hasattr(r, "model_dump") else r))
            # Merge LLM requirements with deterministic keywords/categories
            base = extract_deterministic(text)
            return RequirementsResult(requirements=validated[:20], keywords=base.keywords, categories=base.categories)
        except Exception:
            pass  # fall through to deterministic
        # retry once is handled by caller if needed; here we just fallback
    return extract_deterministic(text)
