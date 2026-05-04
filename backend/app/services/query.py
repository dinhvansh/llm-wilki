from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
import re
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.embedding_client import embedding_client
from app.core.ingest import score_text
from app.core.llm_client import llm_client
from app.core.runtime_config import load_runtime_snapshot
from app.models import ChatMessage, ChatSession, Claim, Page, PageSourceLink, Source, SourceChunk
from app.core.ingest import build_tags, slugify, summarize_text
from app.services.audit import create_audit_log
from app.services.pages import create_page_with_version


IMAGE_URL_RE = re.compile(r"http://localhost:8000/uploads/[^\s)]+", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
FOLLOW_UP_PREFIXES = (
    "cái đó",
    "cai do",
    "cái này",
    "cai nay",
    "ý tôi là",
    "y toi la",
    "nó",
    "no ",
    "trả lời sai rồi",
    "tra loi sai roi",
    "so sánh",
    "so sanh",
    "cái trên",
    "cai tren",
)
AMBIGUOUS_FOLLOWUPS = {
    "trả lời sai rồi",
    "tra loi sai roi",
    "cái đó thì sao",
    "cai do thi sao",
    "nó là gì",
    "no la gi",
    "so sánh cái này",
    "so sanh cai nay",
}
INTENT_KEYWORDS = {
    "definition": ("là gì", "la gi", "định nghĩa", "dinh nghia", "meaning", "define"),
    "procedure": ("quy trình", "quy trinh", "các bước", "cac buoc", "step", "how to", "thiết lập", "thiet lap"),
    "comparison": ("so sánh", "so sanh", "khác gì", "khac gi", "compare", "difference"),
    "policy_rule": ("phải", "must", "required", "policy", "quy định", "quy dinh", "rule"),
    "threshold": ("bao nhiêu", "bao nhieu", "threshold", "mức", "muc", "limit", "sla"),
    "timeline": ("khi nào", "khi nao", "timeline", "mốc", "moc", "date"),
    "conflict_check": ("mâu thuẫn", "mau thuan", "xung đột", "xung dot", "conflict"),
    "source_lookup": ("nguồn", "nguon", "source", "tài liệu nào", "tai lieu nao"),
    "summary": ("tóm tắt", "tom tat", "overview", "summary"),
}


def _tokenize(value: str) -> list[str]:
    return [token for token in value.lower().replace("\n", " ").split() if token]


def _vectorize(value: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for token in _tokenize(value):
        counts[token] = counts.get(token, 0.0) + 1.0
    return counts


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    if dot <= 0:
        return 0.0
    left_norm = sqrt(sum(weight * weight for weight in left.values()))
    right_norm = sqrt(sum(weight * weight for weight in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _hybrid_score(query: str, text: str, title: str | None = None, semantic_weight: float = 0.35) -> float:
    lexical = score_text(query, text)
    semantic = _cosine_similarity(_vectorize(query), _vectorize(text))
    title_bonus = score_text(query, title or "") * 0.35 if title else 0.0
    lexical_weight = max(0.0, 1.0 - semantic_weight)
    return lexical * lexical_weight + semantic * semantic_weight + title_bonus


def _score_components(query: str, text: str, title: str | None, semantic_weight: float, query_embedding: list[float] | None = None, chunk_embedding: list[float] | None = None) -> dict:
    lexical = score_text(query, text)
    if query_embedding and chunk_embedding:
        vector = embedding_client.cosine_similarity(query_embedding, chunk_embedding)
        vector_backend = "provider_embedding"
    else:
        vector = _cosine_similarity(_vectorize(query), _vectorize(text))
        vector_backend = "token_vector_fallback"
    title_bonus = score_text(query, title or "") * 0.35 if title else 0.0
    lexical_weight = max(0.0, 1.0 - semantic_weight)
    final = lexical * lexical_weight + vector * semantic_weight + title_bonus
    return {
        "lexicalScore": round(lexical, 6),
        "vectorScore": round(vector, 6),
        "titleBonus": round(title_bonus, 6),
        "finalScore": round(final, 6),
        "semanticWeight": round(semantic_weight, 6),
        "vectorBackend": vector_backend,
    }


def _hybrid_score_with_embedding(
    query: str,
    text: str,
    query_embedding: list[float] | None,
    chunk_embedding: list[float] | None,
    title: str | None = None,
    semantic_weight: float = 0.35,
) -> float:
    lexical = score_text(query, text)
    if query_embedding and chunk_embedding:
        semantic = embedding_client.cosine_similarity(query_embedding, chunk_embedding)
    else:
        semantic = _cosine_similarity(_vectorize(query), _vectorize(text))
    title_bonus = score_text(query, title or "") * 0.35 if title else 0.0
    lexical_weight = max(0.0, 1.0 - semantic_weight)
    return lexical * lexical_weight + semantic * semantic_weight + title_bonus


def _extract_chunk_embedding(chunk: SourceChunk) -> list[float]:
    metadata = chunk.metadata_json or {}
    embedding = metadata.get("embedding")
    return embedding if isinstance(embedding, list) else []


def _query_terms(value: str) -> list[str]:
    return [token for token in _tokenize(value) if len(token) >= 3]


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _recent_session_messages(db: Session, session_id: str | None, limit: int = 6) -> list[ChatMessage]:
    if not session_id:
        return []
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()[::-1]
    )


def _recent_user_questions(messages: list[ChatMessage]) -> list[str]:
    return [message.content.strip() for message in messages if message.role == "user" and message.content.strip()]


def _extract_recent_entities(messages: list[ChatMessage]) -> list[str]:
    entities: list[str] = []
    for message in messages:
        payload = message.response_json or {}
        interpreted = payload.get("interpretedQuery") or {}
        entities.extend(str(item) for item in interpreted.get("targetEntities", []) if item)
        for page in payload.get("relatedPages", []) or []:
            title = str(page.get("title") or "").strip()
            if title:
                entities.append(title)
        for source in payload.get("relatedSources", []) or []:
            title = str(source.get("title") or "").strip()
            if title:
                entities.append(title)
    return _dedupe_keep_order(entities)[:6]


def _detect_intent(question: str) -> str:
    lowered = question.lower()
    for intent, patterns in INTENT_KEYWORDS.items():
        if any(pattern in lowered for pattern in patterns):
            return intent
    if any(prefix in lowered for prefix in ("trả lời sai", "tra loi sai", "ý tôi là", "y toi la")):
        return "correction_followup"
    return "fact_lookup"


def _answer_type_for_intent(intent: str) -> str:
    return {
        "definition": "definition",
        "procedure": "step_by_step",
        "comparison": "comparison",
        "policy_rule": "policy",
        "threshold": "threshold",
        "timeline": "timeline",
        "conflict_check": "conflict",
        "source_lookup": "source_lookup",
        "summary": "summary",
        "correction_followup": "clarified_answer",
    }.get(intent, "direct_answer")


def _is_followup_style(question: str) -> bool:
    lowered = question.strip().lower()
    return any(lowered.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES)


def _build_query_understanding(question: str, recent_messages: list[ChatMessage], collection_id: str | None = None, page_id: str | None = None) -> dict:
    trimmed = re.sub(r"\s+", " ", question.strip())
    recent_questions = _recent_user_questions(recent_messages)
    recent_entities = _extract_recent_entities(recent_messages)
    intent = _detect_intent(trimmed)
    answer_type = _answer_type_for_intent(intent)
    standalone_query = trimmed
    needs_clarification = False
    clarification_question = None
    conversation_summary = None

    if recent_questions:
        conversation_summary = f"Recent user focus: {' | '.join(recent_questions[-2:])}"

    lowered = trimmed.lower()
    if lowered in AMBIGUOUS_FOLLOWUPS or (len(_query_terms(trimmed)) <= 2 and _is_followup_style(trimmed)):
        needs_clarification = True
        clarification_question = "Bạn đang muốn sửa hoặc hỏi lại phần nào? Hãy nêu rõ chủ đề, thuật ngữ, hoặc bước cụ thể trong tài liệu."

    elif _is_followup_style(trimmed) and recent_questions:
        last_question = recent_questions[-1]
        if any(marker in lowered for marker in ("ý tôi là", "y toi la")):
            suffix = re.split(r"ý tôi là|y toi la", trimmed, flags=re.IGNORECASE, maxsplit=1)[-1].strip(" :,-")
            if suffix:
                standalone_query = f"{last_question}. Focus on: {suffix}"
            else:
                needs_clarification = True
        elif any(marker in lowered for marker in ("so sánh", "so sanh")) and recent_entities:
            standalone_query = f"So sánh {' và '.join(recent_entities[:2])} trong ngữ cảnh: {last_question}"
        elif any(marker in lowered for marker in ("nó", "no", "cái đó", "cai do", "cái này", "cai nay", "cái trên", "cai tren")):
            subject = recent_entities[0] if recent_entities else last_question
            standalone_query = f"{trimmed} trong ngữ cảnh của: {subject}"
        elif any(marker in lowered for marker in ("trả lời sai", "tra loi sai")):
            needs_clarification = True
            clarification_question = "Phần nào trong câu trả lời trước đang sai? Hãy chỉ rõ thuật ngữ, số liệu, hoặc bước bạn muốn sửa."

    target_entities = _dedupe_keep_order(
        recent_entities
        + re.findall(r'"([^"]+)"', trimmed)
        + re.findall(r"'([^']+)'", trimmed)
    )[:6]
    filters = {}
    if collection_id:
        filters["collection_id"] = collection_id
    if page_id:
        filters["page_id"] = page_id

    return {
        "standaloneQuery": standalone_query,
        "intent": intent,
        "answerType": answer_type,
        "targetEntities": target_entities,
        "filters": filters,
        "needsClarification": needs_clarification,
        "clarificationQuestion": clarification_question,
        "conversationSummary": conversation_summary,
    }


def _source_priority(source: Source) -> tuple[float, dict]:
    metadata = source.metadata_json or {}
    trust_score = {"high": 0.18, "medium": 0.1, "low": 0.03}.get((source.trust_level or "").lower(), 0.05)
    authority_level = str(metadata.get("authorityLevel") or metadata.get("authority_level") or "").lower()
    authority_score = {
        "official": 0.18,
        "reference": 0.1,
        "informal": 0.04,
        "user_note": 0.02,
    }.get(authority_level, trust_score)
    source_status = str(metadata.get("sourceStatus") or metadata.get("source_status") or "").lower()
    approval_score = {
        "approved": 0.14,
        "published": 0.12,
        "uploaded": 0.05,
        "draft": 0.02,
        "archived": -0.04,
    }.get(source_status, 0.05)
    freshness_score = 0.02
    if source.updated_at:
        updated_at = source.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - updated_at).days, 0)
        freshness_score = max(-0.02, 0.08 - min(age_days / 3650, 0.1))
    total = round(authority_score + approval_score + freshness_score, 6)
    return total, {
        "authorityScore": round(authority_score, 6),
        "approvalScore": round(approval_score, 6),
        "freshnessScore": round(freshness_score, 6),
        "sourceStatus": source_status or None,
        "authorityLevel": authority_level or None,
    }


def _metadata_match_score(intent: str, collection_id: str | None, source: Source | None = None, page: Page | None = None) -> float:
    score = 0.0
    if collection_id:
        if source and source.collection_id == collection_id:
            score += 0.08
        if page and page.collection_id == collection_id:
            score += 0.08
    if intent == "policy_rule" and source and source.source_type in {"pdf", "docx", "markdown"}:
        score += 0.04
    if intent == "procedure" and source and source.source_type in {"docx", "markdown", "transcript"}:
        score += 0.04
    if intent in {"definition", "summary"} and page:
        score += 0.03
    return round(score, 6)


def _serialize_candidate(candidate_type: str, candidate_id: str, diagnostics: dict, excerpt: str, source: Source | None = None, page: Page | None = None, section_title: str | None = None) -> dict:
    return {
        "candidateType": candidate_type,
        "candidateId": candidate_id,
        "sourceId": source.id if source else None,
        "pageId": page.id if page else None,
        "sourceTitle": source.title if source else (page.title if page else None),
        "sectionTitle": section_title,
        "excerpt": excerpt[:240],
        **diagnostics,
    }


def _retrieve_candidates(
    db: Session,
    runtime,
    interpreted: dict,
    query_embedding: list[float] | None,
) -> list[dict]:
    question = interpreted["standaloneQuery"]
    intent = interpreted["intent"]
    collection_id = interpreted.get("filters", {}).get("collection_id")
    terms = _query_terms(question)
    candidates: list[dict] = []

    chunk_query = db.query(SourceChunk, Source).join(Source, SourceChunk.source_id == Source.id)
    if collection_id:
        chunk_query = chunk_query.filter(Source.collection_id == collection_id)
    if terms:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([SourceChunk.content.ilike(like), SourceChunk.section_title.ilike(like), Source.title.ilike(like)])
        chunk_query = chunk_query.filter(or_(*filters))
    for chunk, source in chunk_query.limit(max(runtime.retrieval_limit * 16, 120)).all():
        diagnostics = _score_components(question, chunk.content, f"{source.title} {chunk.section_title}", runtime.hybrid_semantic_weight, query_embedding, _extract_chunk_embedding(chunk))
        metadata_score = _metadata_match_score(intent, collection_id, source=source)
        authority_total, authority_details = _source_priority(source)
        final = diagnostics["finalScore"] + metadata_score + authority_total
        diagnostics.update({
            "metadataScore": round(metadata_score, 6),
            "authorityScore": round(authority_total, 6),
            "finalScore": round(final, 6),
            **authority_details,
        })
        if final > 0:
            candidates.append(
                {
                    "type": "chunk",
                    "id": chunk.id,
                    "score": final,
                    "source": source,
                    "chunk": chunk,
                    "page": None,
                    "claim": None,
                    "text": chunk.content,
                    "excerpt": chunk.content[:220],
                    "diagnostics": diagnostics,
                }
            )

    claim_query = db.query(Claim, SourceChunk, Source).join(SourceChunk, Claim.source_chunk_id == SourceChunk.id).join(Source, SourceChunk.source_id == Source.id)
    if collection_id:
        claim_query = claim_query.filter(Source.collection_id == collection_id)
    if terms:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([Claim.text.ilike(like), Claim.topic.ilike(like), Source.title.ilike(like)])
        claim_query = claim_query.filter(or_(*filters))
    for claim, chunk, source in claim_query.limit(max(runtime.retrieval_limit * 10, 80)).all():
        diagnostics = _score_components(question, claim.text, claim.topic or source.title, runtime.hybrid_semantic_weight)
        metadata_score = _metadata_match_score(intent, collection_id, source=source)
        authority_total, authority_details = _source_priority(source)
        verification_boost = 0.05 if claim.review_status == "approved" or claim.canonical_status == "verified" else 0.0
        final = diagnostics["finalScore"] + metadata_score + authority_total + verification_boost
        diagnostics.update({
            "metadataScore": round(metadata_score + verification_boost, 6),
            "authorityScore": round(authority_total, 6),
            "finalScore": round(final, 6),
            **authority_details,
        })
        if final > 0:
            candidates.append(
                {
                    "type": "claim",
                    "id": claim.id,
                    "score": final,
                    "source": source,
                    "chunk": chunk,
                    "page": None,
                    "claim": claim,
                    "text": claim.text,
                    "excerpt": claim.text[:220],
                    "diagnostics": diagnostics,
                }
            )

    page_query = db.query(Page)
    if collection_id:
        page_query = page_query.filter(Page.collection_id == collection_id)
    if terms:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([Page.title.ilike(like), Page.summary.ilike(like), Page.content_md.ilike(like)])
        page_query = page_query.filter(or_(*filters))
    for page in page_query.limit(max(runtime.retrieval_limit * 8, 60)).all():
        text = f"{page.title}\n{page.summary}\n{page.content_md[:1200]}"
        diagnostics = _score_components(question, text, page.title, runtime.hybrid_semantic_weight)
        metadata_score = _metadata_match_score(intent, collection_id, page=page)
        final = diagnostics["finalScore"] + metadata_score + (0.05 if page.status == "published" else 0.02 if page.status == "in_review" else 0.0)
        diagnostics.update({
            "metadataScore": round(metadata_score, 6),
            "authorityScore": round(0.05 if page.status == "published" else 0.0, 6),
            "finalScore": round(final, 6),
        })
        if final > 0:
            candidates.append(
                {
                    "type": "page_summary",
                    "id": page.id,
                    "score": final,
                    "source": None,
                    "chunk": None,
                    "page": page,
                    "claim": None,
                    "text": page.summary or page.content_md[:240],
                    "excerpt": (page.summary or page.content_md[:220]),
                    "diagnostics": diagnostics,
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def _rerank_candidates(candidates: list[dict], interpreted: dict, limit: int = 12) -> list[dict]:
    intent = interpreted["intent"]
    target_entities = [entity.lower() for entity in interpreted.get("targetEntities", [])]
    reranked: list[dict] = []
    for index, candidate in enumerate(candidates[:limit]):
        bonus = 0.0
        reasons: list[str] = []
        text_lower = (candidate.get("text") or "").lower()
        if target_entities and any(entity in text_lower for entity in target_entities):
            bonus += 0.08
            reasons.append("entity_match")
        if intent == "definition" and candidate["type"] in {"page_summary", "claim"}:
            bonus += 0.07
            reasons.append("definition_surface")
        elif intent == "procedure" and candidate["type"] == "chunk":
            bonus += 0.08
            reasons.append("procedure_chunk")
        elif intent in {"policy_rule", "threshold", "conflict_check"} and candidate["type"] == "claim":
            bonus += 0.08
            reasons.append("policy_claim")
        if candidate["type"] == "page_summary" and candidate.get("page") and candidate["page"].status == "published":
            bonus += 0.03
            reasons.append("published_page")
        rerank_score = round(candidate["score"] + bonus - (index * 0.002), 6)
        candidate["rerank_score"] = rerank_score
        candidate["diagnostics"]["rerankScore"] = rerank_score
        candidate["diagnostics"]["rerankReason"] = ", ".join(reasons) if reasons else "baseline_score"
        reranked.append(candidate)
    reranked.extend(candidates[limit:])
    reranked.sort(key=lambda item: item.get("rerank_score", item["score"]), reverse=True)
    return reranked


def _build_context_pack(candidates: list[dict], interpreted: dict, limit: int) -> tuple[list[dict], list[dict], dict]:
    intent = interpreted["intent"]
    selected: list[dict] = []
    context_pack: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    desired_roles = ["definition", "evidence", "exception"] if intent == "policy_rule" else ["summary", "evidence", "detail"] if intent in {"definition", "summary"} else ["purpose", "step", "exception"] if intent == "procedure" else ["evidence", "comparison", "detail"]

    def candidate_role(candidate: dict) -> str:
        if candidate["type"] == "page_summary":
            return "summary"
        if candidate["type"] == "claim":
            if intent in {"policy_rule", "threshold", "conflict_check"}:
                return "evidence"
            return "detail"
        chunk = candidate.get("chunk")
        title = (chunk.section_title if chunk else "") if chunk else ""
        lowered = title.lower()
        if "exception" in lowered or "warning" in lowered:
            return "exception"
        if "step" in lowered or intent == "procedure":
            return "step"
        return "evidence"

    for role in desired_roles:
        for candidate in candidates:
            key = (candidate["type"], candidate["id"])
            if key in seen_keys:
                continue
            resolved_role = candidate_role(candidate)
            if resolved_role != role:
                continue
            seen_keys.add(key)
            selected.append(candidate)
            context_pack.append(
                {
                    "role": role,
                    "candidateType": candidate["type"],
                    "candidateId": candidate["id"],
                    "sourceId": candidate["source"].id if candidate.get("source") else None,
                    "pageId": candidate["page"].id if candidate.get("page") else None,
                    "text": candidate["text"][:800],
                }
            )
            if len(selected) >= limit:
                coverage = {
                    f"has_{name}": any(item["role"] == name for item in context_pack)
                    for name in desired_roles
                }
                return selected, context_pack, coverage
            break

    for candidate in candidates:
        key = (candidate["type"], candidate["id"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        selected.append(candidate)
        context_pack.append(
            {
                "role": candidate_role(candidate),
                "candidateType": candidate["type"],
                "candidateId": candidate["id"],
                "sourceId": candidate["source"].id if candidate.get("source") else None,
                "pageId": candidate["page"].id if candidate.get("page") else None,
                "text": candidate["text"][:800],
            }
        )
        if len(selected) >= limit:
            break

    coverage = {
        f"has_{name}": any(item["role"] == name for item in context_pack)
        for name in desired_roles
    }
    coverage["selectedCount"] = len(context_pack)
    return selected, context_pack, coverage


def _extract_first_number(text: str) -> float | None:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\b", text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _build_conflicts(candidates: list[dict], interpreted: dict) -> list[dict]:
    if interpreted["intent"] not in {"policy_rule", "threshold", "conflict_check", "correction_followup"}:
        return []
    sourced = [candidate for candidate in candidates if candidate.get("source")]
    if len(sourced) < 2:
        return []
    distinct: list[dict] = []
    seen_sources: set[str] = set()
    for candidate in sourced:
        source_id = candidate["source"].id
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        distinct.append(candidate)
        if len(distinct) >= 2:
            break
    if len(distinct) < 2:
        return []
    first, second = distinct[0], distinct[1]
    first_value = _extract_first_number(first.get("text", ""))
    second_value = _extract_first_number(second.get("text", ""))
    similar_score = abs(first["score"] - second["score"]) <= 0.35
    value_conflict = first_value is not None and second_value is not None and first_value != second_value
    if not (similar_score or value_conflict):
        return []
    preferred, competing = (first, second) if first["diagnostics"].get("authorityScore", 0) >= second["diagnostics"].get("authorityScore", 0) else (second, first)
    return [
        {
            "summary": "Có nhiều nguồn liên quan với mức ưu tiên khác nhau; nên ưu tiên nguồn có authority/trust cao hơn.",
            "preferredSourceId": preferred["source"].id,
            "preferredSourceTitle": preferred["source"].title,
            "preferredReason": f"Authority score {preferred['diagnostics'].get('authorityScore', 0)}",
            "competingSourceId": competing["source"].id,
            "competingSourceTitle": competing["source"].title,
            "competingReason": f"Authority score {competing['diagnostics'].get('authorityScore', 0)}",
        }
    ]


def _format_answer_sections(question: str, selected: list[dict], interpreted: dict, conflicts: list[dict], uncertainty: str | None = None) -> str:
    if not selected:
        return (
            "## Direct Answer\n\n"
            f"Tôi chưa tìm thấy đủ bằng chứng grounded để trả lời **{question}** trong knowledge base hiện tại.\n\n"
            "## Uncertainty / Missing Evidence\n\n"
            "Hãy thử nêu rõ tên tài liệu, thuật ngữ, hoặc bước cụ thể xuất hiện trong source."
        )
    direct = selected[0]["text"][:320].strip()
    lines = ["## Direct Answer", "", direct, "", "## Evidence", ""]
    for candidate in selected[:3]:
        label = candidate["source"].title if candidate.get("source") else candidate["page"].title if candidate.get("page") else candidate["type"]
        lines.append(f"- **{label}** ({candidate['type']}): {candidate['excerpt'].strip()}")
    if conflicts:
        lines.extend(["", "## Conflicts", ""])
        for conflict in conflicts:
            lines.append(
                f"- {conflict['summary']} Preferred: **{conflict.get('preferredSourceTitle') or 'N/A'}**. "
                f"Competing: **{conflict.get('competingSourceTitle') or 'N/A'}**."
            )
    if uncertainty:
        lines.extend(["", "## Uncertainty / Missing Evidence", "", uncertainty])
    return "\n".join(lines).strip()


def _build_clarification_response(session_id: str, question: str, interpreted: dict, runtime) -> dict:
    answer = interpreted.get("clarificationQuestion") or "Tôi cần thêm ngữ cảnh trước khi trả lời chính xác."
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"ask-{uuid4().hex[:8]}",
        "sessionId": session_id,
        "question": question,
        "answer": answer,
        "answerType": "clarification",
        "interpretedQuery": interpreted,
        "citations": [],
        "relatedPages": [],
        "relatedSources": [],
        "confidence": 18.0,
        "isInference": False,
        "uncertainty": "Current follow-up query is ambiguous without more detail from the user.",
        "conflicts": [],
        "retrievalDebugId": None,
        "diagnostics": {
            "candidateCount": 0,
            "retrievalLimit": runtime.retrieval_limit,
            "searchResultLimit": runtime.search_result_limit,
            "clarificationTriggered": True,
            "topChunks": [],
            "topCandidates": [],
            "selectedContext": [],
            "contextCoverage": {},
        },
        "answeredAt": now_iso,
    }


def _build_citation_payload(index: int, score: float, chunk: SourceChunk, source: Source, query: str) -> dict:
    span = _extract_citation_span(query, chunk.content)
    return {
        "id": f"cit-{index}",
        "index": index,
        "sourceId": source.id,
        "sourceTitle": source.title,
        "chunkId": chunk.id,
        "snippet": span["snippet"],
        "matchedText": span["matchedText"],
        "chunkSpanStart": span["chunkSpanStart"],
        "chunkSpanEnd": span["chunkSpanEnd"],
        "sourceSpanStart": chunk.span_start + span["chunkSpanStart"] if span["chunkSpanStart"] is not None else None,
        "sourceSpanEnd": chunk.span_start + span["chunkSpanEnd"] if span["chunkSpanEnd"] is not None else None,
        "pageId": None,
        "pageTitle": None,
        "url": source.url,
        "confidence": round(min(score * 100, 99), 2),
    }


def _extract_citation_span(query: str, content: str) -> dict:
    text = content.strip()
    if not text:
        return {
            "snippet": "",
            "matchedText": None,
            "chunkSpanStart": None,
            "chunkSpanEnd": None,
        }

    query_terms = _query_terms(query)
    best_match = None
    cursor = 0
    for part in SENTENCE_SPLIT_RE.split(text):
        sentence = part.strip()
        if not sentence:
            cursor += len(part) + 1
            continue
        start = text.find(sentence, cursor)
        if start == -1:
            start = text.find(sentence)
        end = start + len(sentence)
        cursor = end
        lexical = score_text(query, sentence)
        overlap = sum(1 for term in query_terms if term in sentence.lower())
        score = lexical + overlap * 0.2
        if best_match is None or score > best_match["score"]:
            best_match = {
                "score": score,
                "matchedText": sentence,
                "chunkSpanStart": start,
                "chunkSpanEnd": end,
            }

    if best_match is None or best_match["score"] <= 0:
        lowered = text.lower()
        first_term_pos = min((lowered.find(term) for term in query_terms if lowered.find(term) != -1), default=-1)
        if first_term_pos != -1:
            start = max(0, first_term_pos - 80)
            end = min(len(text), first_term_pos + 200)
            matched = text[first_term_pos:min(len(text), first_term_pos + 120)].strip()
            best_match = {
                "matchedText": matched or text[start:end].strip(),
                "chunkSpanStart": first_term_pos,
                "chunkSpanEnd": min(len(text), first_term_pos + max(len(matched), 1)),
            }
        else:
            preview_end = min(len(text), 220)
            best_match = {
                "matchedText": text[:preview_end].strip(),
                "chunkSpanStart": 0,
                "chunkSpanEnd": preview_end,
            }

    snippet_start = max(0, best_match["chunkSpanStart"] - 90)
    snippet_end = min(len(text), best_match["chunkSpanEnd"] + 140)
    snippet = text[snippet_start:snippet_end].strip()
    if snippet_start > 0:
        snippet = f"...{snippet}"
    if snippet_end < len(text):
        snippet = f"{snippet}..."

    return {
        "snippet": snippet,
        "matchedText": best_match["matchedText"],
        "chunkSpanStart": best_match["chunkSpanStart"],
        "chunkSpanEnd": best_match["chunkSpanEnd"],
    }


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _serialize_chat_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "sessionId": message.session_id,
        "role": message.role,
        "content": message.content,
        "response": message.response_json,
        "createdAt": _iso(message.created_at),
    }


def _serialize_chat_session(session: ChatSession, message_count: int | None = None, last_preview: str | None = None) -> dict:
    messages = sorted(session.messages, key=lambda item: item.created_at) if session.messages else []
    if message_count is None:
        message_count = len(messages)
    if last_preview is None and messages:
        last_preview = messages[-1].content[:160]
    return {
        "id": session.id,
        "title": session.title,
        "createdAt": _iso(session.created_at),
        "updatedAt": _iso(session.updated_at),
        "messageCount": message_count,
        "lastMessagePreview": last_preview,
    }


def list_chat_sessions(db: Session, limit: int = 30) -> list[dict]:
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit).all()
    return [_serialize_chat_session(session) for session in sessions]


def get_chat_session(db: Session, session_id: str) -> dict | None:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return None
    data = _serialize_chat_session(session)
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    data["messages"] = [_serialize_chat_message(message) for message in messages]
    data["messageCount"] = len(messages)
    data["lastMessagePreview"] = messages[-1].content[:160] if messages else None
    return data


def delete_chat_session(db: Session, session_id: str) -> bool:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def save_answer_as_draft_page(db: Session, message_id: str, title: str | None = None, owner: str = "Current User") -> dict | None:
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.role == "assistant").first()
    if not message or not message.response_json:
        return None
    response = message.response_json or {}
    page_title = (title or response.get("question") or "Ask Answer Draft").strip()[:160]
    citation_lines = []
    source_ids: list[str] = []
    for citation in response.get("citations", []) or []:
        source_id = citation.get("sourceId")
        if source_id and source_id not in source_ids:
            source_ids.append(source_id)
        citation_lines.append(
            f"- {citation.get('sourceTitle', 'Source')} / chunk `{citation.get('chunkId')}`: {citation.get('snippet', '')[:240]}"
        )
    content_md = "\n".join(
        [
            f"# {page_title}",
            "",
            response.get("answer") or message.content,
            "",
            "## Source Citations",
            "",
            *(citation_lines or ["- Add citations before publishing."]),
        ]
    ).strip()
    summary, key_facts = summarize_text(page_title, content_md[:16000])
    slug_root = slugify(page_title) or f"ask-answer-{uuid4().hex[:6]}"
    slug = slug_root
    suffix = 1
    while db.query(Page).filter(Page.slug == slug).first():
        suffix += 1
        slug = f"{slug_root}-{suffix}"
    page = create_page_with_version(
        db,
        title=page_title,
        slug=slug,
        summary=summary,
        content_md=content_md,
        owner=owner,
        page_type="summary",
        status="draft",
        tags=build_tags(page_title, content_md),
        key_facts=key_facts,
        related_source_ids=source_ids,
        related_entity_ids=[],
    )
    create_audit_log(
        db,
        action="save_ask_answer",
        object_type="page",
        object_id=page.id,
        actor=owner,
        summary=f"Saved Ask answer as draft page `{page_title}`",
        metadata={"messageId": message_id, "sessionId": message.session_id, "sourceIds": source_ids},
    )
    db.commit()
    from app.services.pages import get_page_by_slug

    return get_page_by_slug(db, page.slug)


def _ensure_chat_session(db: Session, session_id: str | None, question: str) -> ChatSession:
    now = datetime.now(timezone.utc)
    if session_id:
        existing = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if existing:
            return existing
    title = re.sub(r"\s+", " ", question.strip())[:72] or "New chat"
    session = ChatSession(id=f"chat-{uuid4().hex[:8]}", title=title, created_at=now, updated_at=now)
    db.add(session)
    db.flush()
    return session


def search(db: Session, query: str, result_type: str = "all", limit: int = 10) -> list[dict]:
    runtime = load_runtime_snapshot(db)
    limit = max(1, min(limit, runtime.search_result_limit, 100))
    query_embedding = _embed_query(runtime, query)
    results: list[dict] = []
    terms = _query_terms(query)

    if result_type in {"all", "page"}:
        page_query = db.query(Page)
        if terms:
            filters = []
            for term in terms[:6]:
                like = f"%{term}%"
                filters.extend([Page.title.ilike(like), Page.summary.ilike(like), Page.content_md.ilike(like)])
            page_query = page_query.filter(or_(*filters))
        for page in page_query.limit(max(limit * 5, 50)).all():
            text = f"{page.title}\n{page.summary}\n{page.content_md}"
            diagnostics = _score_components(query, text, page.title, runtime.hybrid_semantic_weight)
            score = diagnostics["finalScore"]
            if score > 0:
                results.append(
                    {
                        "id": page.id,
                        "type": "page",
                        "title": page.title,
                        "excerpt": page.summary or page.content_md[:180],
                        "pageId": page.id,
                        "pageSlug": page.slug,
                        "sourceId": None,
                        "relevanceScore": round(score * 100, 2),
                        "status": page.status,
                        "diagnostics": diagnostics,
                    }
                )

    if result_type in {"all", "chunk"}:
        chunk_query = db.query(SourceChunk, Source).join(Source, SourceChunk.source_id == Source.id)
        if terms:
            filters = []
            for term in terms[:6]:
                like = f"%{term}%"
                filters.extend([SourceChunk.content.ilike(like), SourceChunk.section_title.ilike(like), Source.title.ilike(like)])
            chunk_query = chunk_query.filter(or_(*filters))
        for chunk, source in chunk_query.limit(max(limit * 8, 80)).all():
            diagnostics = _score_components(
                query,
                chunk.content,
                f"{source.title} {chunk.section_title}",
                runtime.hybrid_semantic_weight,
                query_embedding,
                _extract_chunk_embedding(chunk),
            )
            score = diagnostics["finalScore"]
            if score > 0:
                results.append(
                    {
                        "id": chunk.id,
                        "type": "chunk",
                        "title": f"{source.title} ({chunk.section_title})",
                        "excerpt": chunk.content[:220],
                        "pageId": None,
                        "pageSlug": None,
                        "sourceId": source.id,
                        "relevanceScore": round(score * 100, 2),
                        "status": None,
                        "diagnostics": diagnostics,
                    }
                )

    if result_type in {"all", "claim"}:
        claim_query = db.query(Claim)
        if terms:
            filters = []
            for term in terms[:6]:
                like = f"%{term}%"
                filters.extend([Claim.text.ilike(like), Claim.topic.ilike(like)])
            claim_query = claim_query.filter(or_(*filters))
        for claim in claim_query.limit(max(limit * 5, 50)).all():
            diagnostics = _score_components(query, claim.text, claim.topic or claim.text[:80], runtime.hybrid_semantic_weight)
            score = diagnostics["finalScore"]
            if score > 0:
                results.append(
                    {
                        "id": claim.id,
                        "type": "claim",
                        "title": claim.text[:90],
                        "excerpt": claim.text,
                        "pageId": None,
                        "pageSlug": None,
                        "sourceId": None,
                        "relevanceScore": round(score * 100, 2),
                        "status": None,
                        "diagnostics": diagnostics,
                    }
                )

    results.sort(key=lambda item: item["relevanceScore"], reverse=True)
    return results[:limit]


def ask(db: Session, question: str, session_id: str | None = None, collection_id: str | None = None, page_id: str | None = None) -> dict:
    session = _ensure_chat_session(db, session_id, question)
    runtime = load_runtime_snapshot(db)
    recent_messages = _recent_session_messages(db, session.id)
    interpreted = _build_query_understanding(question, recent_messages, collection_id=collection_id, page_id=page_id)
    if interpreted["needsClarification"]:
        response = _build_clarification_response(session.id, question, interpreted, runtime)
        now = datetime.now(timezone.utc)
        db.add(ChatMessage(id=f"msg-{uuid4().hex[:8]}", session_id=session.id, role="user", content=question, response_json=None, created_at=now))
        db.add(ChatMessage(id=response["id"], session_id=session.id, role="assistant", content=response["answer"], response_json=response, created_at=now))
        session.updated_at = now
        db.commit()
        return response

    standalone_query = interpreted["standaloneQuery"]
    query_embedding = _embed_query(runtime, standalone_query)
    candidates = _retrieve_candidates(db, runtime, interpreted, query_embedding)
    reranked_candidates = _rerank_candidates(candidates, interpreted, limit=max(runtime.retrieval_limit * 3, 12))
    selected_candidates, context_pack, context_coverage = _build_context_pack(reranked_candidates, interpreted, runtime.retrieval_limit)
    top_chunks = [candidate for candidate in selected_candidates if candidate["type"] == "chunk"]

    source_map = {candidate["source"].id: candidate["source"] for candidate in selected_candidates if candidate.get("source")}
    related_pages_map: dict[str, dict] = {}
    if source_map:
        page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id.in_(list(source_map))).all()]
        pages = db.query(Page).filter(Page.id.in_(page_ids)).all() if page_ids else []
        for page in pages[:4]:
            page_score = round(_hybrid_score(standalone_query, f"{page.title}\n{page.summary}\n{page.content_md}", title=page.title, semantic_weight=runtime.hybrid_semantic_weight) * 100, 2)
            related_pages_map[page.id] = {
                "id": page.id,
                "slug": page.slug,
                "title": page.title,
                "pageType": page.page_type,
                "relevanceScore": page_score,
                "excerpt": (page.summary or page.content_md[:180])[:180],
            }
    for candidate in selected_candidates:
        page = candidate.get("page")
        if page and page.id not in related_pages_map:
            related_pages_map[page.id] = {
                "id": page.id,
                "slug": page.slug,
                "title": page.title,
                "pageType": page.page_type,
                "relevanceScore": round(min(candidate["score"] * 100, 99), 2),
                "excerpt": (page.summary or page.content_md[:180])[:180],
            }
    related_pages = list(related_pages_map.values())[:4]

    citations = [
        _build_citation_payload(index, candidate["score"], candidate["chunk"], candidate["source"], standalone_query)
        for index, candidate in enumerate(top_chunks, start=1)
    ]

    related_sources_map: dict[str, dict] = {}
    for candidate in selected_candidates:
        source = candidate.get("source")
        if not source:
            continue
        relevance_score = round(min(candidate["score"] * 100, 99), 2)
        existing = related_sources_map.get(source.id)
        if existing and existing["relevanceScore"] >= relevance_score:
            continue
        related_sources_map[source.id] = {
            "id": source.id,
            "title": source.title,
            "sourceType": source.source_type,
            "trustLevel": source.trust_level,
            "relevanceScore": relevance_score,
        }
    related_sources = list(related_sources_map.values())
    related_images = _collect_related_images(db, [(candidate["score"], candidate["chunk"], candidate["source"]) for candidate in top_chunks], limit=3)

    conflicts = _build_conflicts(reranked_candidates[: max(runtime.retrieval_limit * 3, 8)], interpreted)
    uncertainty = None if selected_candidates else "No grounded evidence was selected from the indexed knowledge base."
    answer = _format_answer_sections(question, selected_candidates, interpreted, conflicts, uncertainty=uncertainty)
    used_llm_answer = False
    if selected_candidates:
        answer_profile = runtime.profile_for_task("ask_answer")
        system_prompt = (
            "You are a grounded internal knowledge-base assistant. "
            "Use only provided evidence. "
            "Return concise markdown with sections: Direct Answer, Evidence, and Uncertainty when needed. "
            "Do not invent facts or citations."
        )
        context_blocks = []
        for item in context_pack:
            source_label = item.get("sourceId") or item.get("pageId") or item.get("candidateId")
            context_blocks.append(f"[Role: {item['role']} | Ref: {source_label}]\n{item['text']}")
        user_prompt = (
            f"Original question: {question}\n"
            f"Interpreted query: {standalone_query}\n"
            f"Intent: {interpreted['intent']}\n\n"
            "Context:\n\n" + "\n\n---\n\n".join(context_blocks)
        )
        llm_answer = llm_client.complete(answer_profile, system_prompt, user_prompt)
        if llm_answer:
            answer = llm_answer.strip()
            used_llm_answer = True
    if related_images:
        answer = _append_related_illustrations(answer, related_images)

    confidence = round(min((selected_candidates[0]["score"] * 100) if selected_candidates else 45, 95), 2)
    response = {
        "id": f"ask-{uuid4().hex[:8]}",
        "sessionId": session.id,
        "question": question,
        "answer": answer,
        "answerType": interpreted["answerType"],
        "interpretedQuery": interpreted,
        "citations": citations,
        "relatedPages": related_pages,
        "relatedSources": related_sources,
        "confidence": confidence,
        "isInference": not used_llm_answer,
        "uncertainty": uncertainty,
        "conflicts": conflicts,
        "retrievalDebugId": f"dbg-{uuid4().hex[:8]}",
        "diagnostics": {
            "candidateCount": len(candidates),
            "retrievalLimit": runtime.retrieval_limit,
            "searchResultLimit": runtime.search_result_limit,
            "clarificationTriggered": False,
            "topChunks": [
                _serialize_candidate("chunk", candidate["chunk"].id, candidate["diagnostics"], candidate["excerpt"], source=candidate["source"], section_title=candidate["chunk"].section_title)
                for candidate in reranked_candidates[: runtime.retrieval_limit * 2]
                if candidate["type"] == "chunk" and candidate.get("chunk")
            ],
            "topCandidates": [
                _serialize_candidate(
                    candidate["type"],
                    candidate["id"],
                    candidate["diagnostics"],
                    candidate["excerpt"],
                    source=candidate.get("source"),
                    page=candidate.get("page"),
                    section_title=candidate["chunk"].section_title if candidate.get("chunk") else None,
                )
                for candidate in reranked_candidates[: runtime.retrieval_limit * 3]
            ],
            "selectedContext": context_pack,
            "contextCoverage": context_coverage,
        },
        "answeredAt": datetime.now(timezone.utc).isoformat(),
    }
    now = datetime.now(timezone.utc)
    db.add(ChatMessage(id=f"msg-{uuid4().hex[:8]}", session_id=session.id, role="user", content=question, response_json=None, created_at=now))
    db.add(ChatMessage(id=response["id"], session_id=session.id, role="assistant", content=answer, response_json=response, created_at=now))
    session.updated_at = now
    if session.title == "New chat":
        session.title = re.sub(r"\s+", " ", question.strip())[:72] or session.title
    db.commit()
    return response


def _source_images_in_document_order(source: Source) -> list[str]:
    metadata = source.metadata_json or {}
    ordered_blocks = metadata.get("orderedBlocks") or []
    image_urls = [
        block.get("url")
        for block in ordered_blocks
        if isinstance(block, dict) and block.get("type") == "image" and block.get("url")
    ]
    if image_urls:
        return image_urls
    return [url for url in metadata.get("images", []) if url]


def _collect_related_images(db: Session, top_chunks: list[tuple], limit: int = 3) -> list[str]:
    image_urls: list[str] = []
    seen: set[str] = set()
    source_order: dict[str, tuple[int, Source]] = {}
    for row in top_chunks:
        _, chunk, source = row[:3]
        current = source_order.get(source.id)
        if current is None or chunk.chunk_index < current[0]:
            source_order[source.id] = (chunk.chunk_index, source)

    for _, source in sorted(source_order.values(), key=lambda item: item[0]):
        for url in _source_images_in_document_order(source):
            if url and url not in seen:
                seen.add(url)
                image_urls.append(url)
                if len(image_urls) >= limit:
                    return image_urls

    source_ids = [row[2].id for row in top_chunks]
    if source_ids:
        page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id.in_(source_ids)).all()]
        if page_ids:
            for page in db.query(Page).filter(Page.id.in_(page_ids)).all():
                for url in IMAGE_URL_RE.findall(page.content_md or ""):
                    if url not in seen:
                        seen.add(url)
                        image_urls.append(url)
                        if len(image_urls) >= limit:
                            return image_urls
    return image_urls


def _append_related_illustrations(answer: str, image_urls: list[str]) -> str:
    if not image_urls:
        return answer
    lines = [answer.rstrip(), "", "## Related Illustrations", ""]
    for index, image_url in enumerate(image_urls, start=1):
        lines.extend([f"![Illustration {index}]({image_url})", ""])
    return "\n".join(lines).strip()


def _embed_query(runtime, query: str) -> list[float] | None:
    vectors = embedding_client.embed_texts(runtime.profile_for_task("embeddings"), [query])
    if not vectors:
        return None
    return vectors[0]


def _build_fallback_answer(question: str, top_chunks: list[tuple]) -> str:
    if not top_chunks:
        return (
            f"I could not find grounded evidence for **{question}** in the indexed sources.\n\n"
            "Try uploading more documents or rephrase the question with terms that appear in the source material."
        )

    lines = [f"## Answer\n", f"Based on the indexed sources, here is the strongest grounded evidence for **{question}**:\n"]
    for row in top_chunks[:3]:
        _, chunk, source = row[:3]
        lines.append(f"- **{source.title}**: {chunk.content[:220].strip()}")
    lines.append("\nThe answer above is generated from lexical retrieval fallback because no external LLM provider is currently configured.")
    return "\n".join(lines)
