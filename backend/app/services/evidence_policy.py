from __future__ import annotations

import re


QUERY_STOPWORDS = {
    "what", "which", "when", "where", "how", "why", "for", "with", "this", "that", "about",
    "required", "should", "would", "could", "into", "from", "before", "after", "the", "and",
    "cai", "nao", "gi", "la", "cho", "voi", "hay", "can", "nen", "nhung",
}


def _tokenize(value: str) -> list[str]:
    return [token for token in value.lower().replace("\n", " ").split() if token]


def _query_terms(value: str) -> list[str]:
    return [token for token in _tokenize(value) if len(token) >= 3]


def _strict_content_terms(value: str) -> list[str]:
    short_domain_terms = {"ai", "qa", "pii", "api", "rag", "ocr", "llm", "bm25"}
    terms: list[str] = []
    seen: set[str] = set()
    for token in _query_terms(value):
        normalized = re.sub(r"[^a-z0-9_-]", "", token.lower())
        if not normalized or normalized in seen or normalized in QUERY_STOPWORDS:
            continue
        if len(normalized) >= 5 or normalized in short_domain_terms:
            terms.append(normalized)
            seen.add(normalized)
    return terms


def candidate_evidence_text(candidate: dict) -> str:
    parts = [
        str(candidate.get("text") or ""),
        str(candidate.get("excerpt") or ""),
    ]
    source = candidate.get("source")
    page = candidate.get("page")
    chunk = candidate.get("chunk")
    claim = candidate.get("claim")
    if source:
        parts.extend([str(source.title or ""), str(source.description or "")])
    if page:
        parts.extend([str(page.title or ""), str(page.summary or "")])
    if chunk:
        parts.append(str(chunk.section_title or ""))
    if claim:
        parts.extend([str(claim.topic or ""), str(claim.text or "")])
    return " ".join(parts)


def candidate_term_coverage(question: str, candidate: dict) -> float:
    terms = _strict_content_terms(question)
    if not terms:
        return 1.0
    evidence_text = re.sub(r"[^a-z0-9_-]+", " ", candidate_evidence_text(candidate).lower())
    return sum(1 for term in terms if term in evidence_text) / max(len(terms), 1)


def candidate_evidence_grade(question: str, candidate: dict) -> dict:
    """Small, deterministic grade used by Ask UI and evals to explain why evidence was cited."""
    coverage = candidate_term_coverage(question, candidate)
    candidate_type = str(candidate.get("type") or "")
    source = candidate.get("source")
    source_status = str(getattr(source, "source_status", "") or "").lower() if source else ""
    trust_level = str(getattr(source, "trust_level", "") or "").lower() if source else ""
    authority_level = str(((getattr(source, "metadata_json", None) or {}) if source else {}).get("authorityLevel") or "").lower()
    specificity = {
        "claim": 0.95,
        "knowledge_unit": 0.9,
        "chunk": 0.85,
        "user_note": 0.82,
        "artifact_summary": 0.8,
        "notebook_note": 0.78,
        "section_summary": 0.7,
        "page_summary": 0.6,
    }.get(candidate_type, 0.55)
    authority = 0.9 if trust_level in {"authoritative", "high"} or authority_level in {"policy", "official", "approved"} else 0.68
    freshness = 0.55 if source_status in {"archived", "deprecated", "stale"} else 0.82
    contradiction_risk = 0.2 if candidate_type in {"claim", "knowledge_unit", "chunk"} else 0.35
    return {
        "relevance": round(float(candidate.get("score") or 0.0), 4),
        "specificity": specificity,
        "authority": authority,
        "freshness": freshness,
        "termCoverage": round(coverage, 4),
        "contradictionRisk": contradiction_risk,
    }


def citation_reason(question: str, candidate: dict) -> str:
    grade = candidate_evidence_grade(question, candidate)
    candidate_type = str(candidate.get("type") or "evidence").replace("_", " ")
    source = candidate.get("source")
    source_title = getattr(source, "title", None) or "the selected source"
    strengths: list[str] = []
    if grade["termCoverage"] >= 0.7:
        strengths.append("strong query-term coverage")
    if grade["specificity"] >= 0.85:
        strengths.append("specific source-level evidence")
    if grade["authority"] >= 0.85:
        strengths.append("high source authority")
    if not strengths:
        strengths.append("best available grounded match")
    return f"Selected {candidate_type} from {source_title} because it has {', '.join(strengths)}."


def select_citation_candidates(question: str, interpreted: dict, selected_candidates: list[dict]) -> list[dict]:
    if not selected_candidates:
        return []
    intent = str(interpreted.get("intent") or "")
    multi_source_intents = {"comparison", "change_review", "conflict_check", "authority_check", "analysis", "risk_review"}
    single_citation_intents = {"definition", "source_lookup", "fact_lookup"}
    max_citations = 4 if intent in multi_source_intents else 1 if intent in single_citation_intents else 2
    min_coverage = 0.5 if intent in multi_source_intents else 0.51
    if interpreted.get("filters", {}).get("source_id"):
        min_coverage = 0.35
        max_citations = min(max_citations, 3)

    ranked: list[tuple[float, dict]] = []
    for index, candidate in enumerate(selected_candidates):
        coverage = candidate_term_coverage(question, candidate)
        type_boost = {
            "claim": 0.08,
            "chunk": 0.07,
            "knowledge_unit": 0.06,
            "artifact_summary": 0.06,
            "notebook_note": 0.05,
            "user_note": 0.05,
            "section_summary": 0.02,
            "page_summary": -0.03,
        }.get(str(candidate.get("type") or ""), 0.0)
        rank_score = coverage * 10 + type_boost + float(candidate.get("score") or 0.0) * 0.03 - index * 0.01
        if coverage >= min_coverage or index == 0:
            ranked.append((rank_score, candidate))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected: list[dict] = []
    seen_sources: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    for _, candidate in ranked:
        key = (str(candidate.get("type") or ""), str(candidate.get("id") or ""))
        if key in seen_keys:
            continue
        source = candidate.get("source")
        source_id = source.id if source else None
        if source_id and source_id in seen_sources and intent not in {"conflict_check", "authority_check"}:
            continue
        selected.append(candidate)
        seen_keys.add(key)
        if source_id:
            seen_sources.add(source_id)
        if len(selected) >= max_citations:
            break
    return selected
