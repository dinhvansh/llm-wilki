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
            "citationCount": len(citations),
            "missingEvidenceRisk": "high",
            "notes": ["No selected evidence candidates were available."],
        }

    coverage = max(candidate_term_coverage(question, candidate) for candidate in selected_candidates)
    evidence_text = " ".join(candidate_evidence_text(candidate) for candidate in selected_candidates[:6])
    evidence_terms = _plain_terms(evidence_text)
    answer_terms = _plain_terms(answer)
    overlap = len(answer_terms & evidence_terms) / max(len(answer_terms), 1)
    citation_count = len(citations)
    notes: list[str] = []
    if citation_count == 0:
        notes.append("Answer has selected evidence but no citation payloads.")
    if coverage < 0.35:
        notes.append("Selected evidence has low query-term coverage.")
    if overlap < 0.2 and len(answer_terms) >= 8:
        notes.append("Answer text has low lexical overlap with selected evidence.")

    intent = str(interpreted.get("intent") or "")
    supported = citation_count > 0 and coverage >= 0.35
    if intent in {"summary", "analysis", "risk_review"}:
        supported = citation_count > 0 and coverage >= 0.2
    return {
        "supported": supported,
        "coverage": round(coverage, 4),
        "answerEvidenceOverlap": round(overlap, 4),
        "citationCount": citation_count,
        "missingEvidenceRisk": "low" if supported else "medium",
        "notes": notes,
    }
