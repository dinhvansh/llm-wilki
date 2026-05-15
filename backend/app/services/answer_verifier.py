from __future__ import annotations

import re

from app.services.evidence_policy import candidate_evidence_text, candidate_term_coverage


def _plain_terms(value: str) -> set[str]:
    return {token for token in re.sub(r"[^a-z0-9_-]+", " ", value.lower()).split() if len(token) >= 4}


def verify_answer_support(
    question: str,
    answer: str,
    interpreted: dict,
    selected_candidates: list[dict],
    citations: list[dict],
) -> dict:
    if not selected_candidates:
        return {
            "supported": False,
            "coverage": 0.0,
            "coverageLevel": "none",
            "finalDecision": "no_answer",
            "risk": "high",
            "citationCount": len(citations),
            "missingEvidenceRisk": "high",
            "unsupportedClaims": [],
            "missingEvidence": ["No selected evidence candidates were available."],
            "notes": ["No selected evidence candidates were available."],
        }

    coverage = max(candidate_term_coverage(question, candidate) for candidate in selected_candidates)
    evidence_text = " ".join(candidate_evidence_text(candidate) for candidate in selected_candidates[:6])
    evidence_terms = _plain_terms(evidence_text)
    answer_terms = _plain_terms(answer)
    overlap = len(answer_terms & evidence_terms) / max(len(answer_terms), 1)
    citation_count = len(citations)
    notes: list[str] = []
    missing_evidence: list[str] = []
    unsupported_claims: list[str] = []
    if citation_count == 0:
        notes.append("Answer has selected evidence but no citation payloads.")
        missing_evidence.append("No citations were generated for this answer.")
    if coverage < 0.35:
        notes.append("Selected evidence has low query-term coverage.")
        missing_evidence.append("Selected evidence has low query-term coverage.")
    if overlap < 0.2 and len(answer_terms) >= 8:
        notes.append("Answer text has low lexical overlap with selected evidence.")
        unsupported_claims.append("Answer may include unsupported statements beyond cited evidence.")
    number_tokens = re.findall(r"\b\d[\d,./-]*\b", answer)
    for token in number_tokens[:8]:
        if token not in evidence_text:
            unsupported_claims.append(f"Numeric/date token `{token}` was not found in selected evidence.")

    intent = str(interpreted.get("intent") or "")
    supported = citation_count > 0 and coverage >= 0.35
    if intent in {"summary", "analysis", "risk_review"}:
        supported = citation_count > 0 and coverage >= 0.2
    coverage_level = "full" if coverage >= 0.55 else "partial" if coverage >= 0.2 else "none"
    if supported and not unsupported_claims:
        final_decision = "answer"
        risk = "low"
    elif citation_count == 0 or coverage < 0.2:
        final_decision = "no_answer"
        risk = "high"
    else:
        final_decision = "partial_answer"
        risk = "medium"
    return {
        "supported": supported,
        "coverage": round(coverage, 4),
        "coverageLevel": coverage_level,
        "finalDecision": final_decision,
        "risk": risk,
        "answerEvidenceOverlap": round(overlap, 4),
        "citationCount": citation_count,
        "missingEvidenceRisk": "low" if risk == "low" else "medium" if risk == "medium" else "high",
        "unsupportedClaims": unsupported_claims,
        "missingEvidence": missing_evidence,
        "notes": notes,
    }
