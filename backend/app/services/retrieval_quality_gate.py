from __future__ import annotations

from app.services.evidence_policy import candidate_evidence_grade, candidate_term_coverage


def evaluate_retrieval_quality(
    question: str,
    interpreted: dict,
    reranked_candidates: list[dict],
    selected_candidates: list[dict],
    context_coverage: dict | None,
    scope_summary: dict | None,
) -> dict:
    selected_count = len(selected_candidates)
    top_score = float(selected_candidates[0]["score"]) if selected_candidates else 0.0
    max_coverage = max((candidate_term_coverage(question, candidate) for candidate in selected_candidates), default=0.0)
    warnings: list[str] = []
    intent = str(interpreted.get("intent") or "")
    scoped = bool(scope_summary and scope_summary.get("strict"))

    if selected_count == 0:
        reason = "no_grounded_candidates"
        if context_coverage and context_coverage.get("scopeExhausted"):
            reason = "scope_exhausted"
            warnings.append("No grounded evidence matched the current strict scope.")
        if context_coverage and context_coverage.get("termCoverageInsufficient"):
            reason = "term_coverage_insufficient"
            warnings.append("Retrieved evidence does not sufficiently cover query terms.")
        return {
            "passed": False,
            "status": "insufficient",
            "reason": reason,
            "warnings": warnings,
            "topScore": round(top_score, 4),
            "coverage": round(max_coverage, 4),
            "selectedCount": selected_count,
            "candidateCount": len(reranked_candidates),
        }

    min_coverage = 0.35
    min_top_score = 0.17
    if intent in {"summary", "analysis", "risk_review"}:
        min_coverage = 0.22
        min_top_score = 0.13
    if scoped:
        min_coverage = max(0.2, min_coverage - 0.1)
        min_top_score = max(0.11, min_top_score - 0.04)

    if max_coverage < min_coverage:
        warnings.append("Selected evidence has low query-term coverage.")
    if top_score < min_top_score:
        warnings.append("Top grounded candidate score is below the policy threshold.")

    contradiction_risk = max(
        (float(candidate_evidence_grade(question, candidate).get("contradictionRisk") or 0.0) for candidate in selected_candidates[:6]),
        default=0.0,
    )
    if contradiction_risk >= 0.45:
        warnings.append("Selected evidence has elevated contradiction risk.")

    strong_evidence = max_coverage >= min_coverage and top_score >= min_top_score
    partial_evidence = max_coverage >= max(0.2, min_coverage - 0.1) and top_score >= max(0.1, min_top_score - 0.05)

    if strong_evidence:
        status = "supported"
        passed = True
        reason = "sufficient_evidence"
    elif partial_evidence:
        status = "partial"
        passed = True
        reason = "partial_evidence"
    else:
        status = "insufficient"
        passed = False
        reason = "weak_evidence"

    return {
        "passed": passed,
        "status": status,
        "reason": reason,
        "warnings": warnings,
        "topScore": round(top_score, 4),
        "coverage": round(max_coverage, 4),
        "selectedCount": selected_count,
        "candidateCount": len(reranked_candidates),
    }
