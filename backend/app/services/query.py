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
from app.models import ChatMessage, ChatSession, Claim, Collection, KnowledgeUnit, Note, NoteAnchor, Page, PageSourceLink, Source, SourceChunk
from app.core.ingest import build_tags, slugify, summarize_text
from app.services.audit import create_audit_log
from app.services.answer_verifier import verify_answer_support
from app.services.context_assembly import assemble_context_pack
from app.services.evidence_policy import candidate_evidence_grade, citation_reason, select_citation_candidates
from app.services.pages import create_page_with_version
from app.services.permissions import can_access_collection_id
from app.services.retrieval_quality_gate import evaluate_retrieval_quality
from app.services.retrieval_candidates import retrieve_candidates


IMAGE_URL_RE = re.compile(r"(?:https?://[^\s)]+/uploads/[^\s)]+|/uploads/[^\s)]+|/backend-uploads/[^\s)]+)", re.IGNORECASE)
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
    "procedure": ("quy trình", "quy trinh", "các bước", "cac buoc", "step", "how to", "thiết lập", "thiet lap", "prepare", "test first", "test", "prerequisite"),
    "comparison": ("so sánh", "so sanh", "khác gì", "khac gi", "compare", "difference"),
    "policy_rule": ("phải", "must", "required", "policy", "quy định", "quy dinh", "rule"),
    "threshold": ("bao nhiêu", "bao nhieu", "threshold", "mức", "muc", "limit", "sla"),
    "timeline": ("khi nào", "khi nao", "timeline", "mốc", "moc", "date"),
    "conflict_check": ("mâu thuẫn", "mau thuan", "xung đột", "xung dot", "conflict"),
    "authority_check": ("authoritative", "authority", "uu tien", "trust more", "which source should be trusted", "official hay informal"),
    "risk_review": ("rui ro", "risk", "caveat", "watch for", "failure point", "luu y"),
    "change_review": ("what changed", "change review", "version change", "between versions", "khac nhau giua ban"),
    "source_lookup": ("nguồn", "nguon", "source", "tài liệu nào", "tai lieu nao"),
    "summary": ("tóm tắt", "tom tat", "overview", "summary"),
}

INTENT_PRIORITY = (
    "conflict_check",
    "authority_check",
    "change_review",
    "comparison",
    "risk_review",
    "procedure",
    "threshold",
    "definition",
    "timeline",
    "source_lookup",
    "summary",
    "policy_rule",
)

SEARCHABLE_SOURCE_STATUSES = {"indexed", "completed"}
SEARCHABLE_PAGE_STATUSES = {"published", "in_review"}
ANSWER_MODE_ANSWER = "answer"
ANSWER_MODE_PARTIAL = "partial_answer"
ANSWER_MODE_NO_ANSWER = "no_answer"
ANSWER_MODE_GENERAL_FALLBACK = "general_fallback"

EVIDENCE_STATUS_SUPPORTED = "supported"
EVIDENCE_STATUS_PARTIAL = "partial"
EVIDENCE_STATUS_INSUFFICIENT = "insufficient"
EVIDENCE_STATUS_UNSUPPORTED = "unsupported"


def _searchable_source_filter(query):
    return query.filter(
        Source.parse_status.in_(SEARCHABLE_SOURCE_STATUSES),
        Source.ingest_status.in_(SEARCHABLE_SOURCE_STATUSES),
    )


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


QUERY_STOPWORDS = {
    "what", "which", "when", "where", "how", "why", "for", "with", "this", "that", "about",
    "required", "should", "would", "could", "into", "from", "before", "after", "the", "and",
    "tell", "most", "important", "summarize", "summary",
    "cai", "nao", "gi", "la", "cho", "voi", "hay", "can", "nen", "nhung", "tom", "tat",
}


def _content_query_terms(value: str) -> list[str]:
    return [token for token in _query_terms(value) if token not in QUERY_STOPWORDS]


def _strict_content_terms(value: str) -> list[str]:
    short_domain_terms = {"ai", "qa", "pii", "api", "rag", "ocr", "llm", "bm25"}
    terms: list[str] = []
    for token in _content_query_terms(value):
        normalized = re.sub(r"[^a-z0-9_-]", "", token.lower())
        if (len(normalized) >= 5 or normalized in short_domain_terms) and normalized not in QUERY_STOPWORDS:
            terms.append(normalized)
    return _dedupe_keep_order(terms)


def _detect_question_language(question: str) -> str:
    lowered = question.lower()
    vietnamese_markers = (" khong ", " tai ", " nguon ", " du lieu ", "chinh sach", "cau hoi")
    if any(marker in f" {lowered} " for marker in vietnamese_markers):
        return "vi"
    if any(ord(char) > 127 for char in question):
        return "vi"
    return "en"


def _looks_english_heavy(text: str) -> bool:
    sample = re.sub(r"\s+", " ", (text or "").strip())[:600]
    if not sample:
        return False
    if any(char in sample for char in "ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"):
        return False
    words = re.findall(r"[A-Za-z]{3,}", sample)
    return len(words) >= 12


def _infer_source_languages(selected_candidates: list[dict]) -> list[str]:
    languages: list[str] = []
    seen: set[str] = set()
    for candidate in selected_candidates:
        source = candidate.get("source")
        metadata = getattr(source, "metadata_json", {}) if source else {}
        language = str((metadata or {}).get("language") or (metadata or {}).get("detectedLanguage") or "").strip().lower()
        if not language:
            evidence = (str(candidate.get("excerpt") or "") + " " + str(candidate.get("text") or "")).strip()
            language = "vi" if any(ord(char) > 127 for char in evidence[:220]) else "en"
        if language and language not in seen:
            seen.add(language)
            languages.append(language)
    return languages or ["unknown"]


def _candidate_collection_id(candidate: dict) -> str | None:
    source = candidate.get("source")
    page = candidate.get("page")
    note = candidate.get("note")
    if source is not None:
        return getattr(source, "collection_id", None)
    if page is not None:
        return getattr(page, "collection_id", None)
    if note is not None:
        return getattr(note, "collection_id", None)
    return None


def _enforce_candidate_permissions(candidates: list[dict], actor) -> tuple[list[dict], int]:
    if actor is None:
        return candidates, 0
    allowed: list[dict] = []
    blocked = 0
    for candidate in candidates:
        collection_id = _candidate_collection_id(candidate)
        if can_access_collection_id(actor, collection_id):
            allowed.append(candidate)
        else:
            blocked += 1
    return allowed, blocked


def _no_answer_text(language: str) -> str:
    if language == "vi":
        return (
            "Tôi chưa tìm thấy đủ bằng chứng liên quan trong knowledge base để trả lời chính xác. "
            "Bạn có thể upload thêm tài liệu liên quan, hỏi cụ thể hơn, hoặc mở rộng phạm vi tìm kiếm."
        )
    return (
        "I could not find enough relevant evidence in the current knowledge base to answer this accurately. "
        "Upload a related source, narrow the question, or expand the search scope."
    )


def _partial_answer_prefix(language: str) -> str:
    if language == "vi":
        return "Tôi chỉ tìm thấy bằng chứng cho một phần câu hỏi. Câu trả lời dưới đây chỉ bao gồm phần có nguồn hỗ trợ."
    return "I found evidence for part of the question, but not enough to answer everything. The answer below only covers the supported portion."


def _build_query_variants(question: str, answer_language: str, *, cross_lingual_enabled: bool = True) -> list[dict]:
    base = re.sub(r"\s+", " ", question.strip())
    variants: list[dict] = [{"id": "v1", "query": base, "language": answer_language, "type": "original"}]
    vi_to_en = {
        "chinh sach": "policy",
        "nghi phep": "annual leave",
        "hoan tien": "refund",
        "quy trinh": "procedure",
        "nguon": "source",
        "du lieu": "data",
    }
    en_to_vi = {
        "policy": "chinh sach",
        "annual leave": "nghi phep",
        "refund": "hoan tien",
        "procedure": "quy trinh",
        "source": "nguon",
        "data": "du lieu",
    }
    lowered = base.lower()
    rewritten = lowered
    mapping = vi_to_en if answer_language == "vi" else en_to_vi
    for src, target in mapping.items():
        rewritten = rewritten.replace(src, target)
    rewritten = re.sub(r"\s+", " ", rewritten).strip()
    if cross_lingual_enabled and rewritten and rewritten != lowered:
        variants.append(
            {
                "id": "v2",
                "query": rewritten,
                "language": "en" if answer_language == "vi" else "vi",
                "type": "cross_lingual_rewrite",
            }
        )
    return variants


def _evidence_covers_question_terms(question: str, selected_candidates: list[dict]) -> bool:
    terms = _strict_content_terms(question)
    if len(terms) < 2 or not selected_candidates:
        return True
    evidence_parts: list[str] = []
    for candidate in selected_candidates[:6]:
        evidence_parts.append(str(candidate.get("text") or ""))
        evidence_parts.append(str(candidate.get("excerpt") or ""))
        source = candidate.get("source")
        page = candidate.get("page")
        if source:
            evidence_parts.append(str(source.title or ""))
            evidence_parts.append(str(source.description or ""))
        if page:
            evidence_parts.append(str(page.title or ""))
            evidence_parts.append(str(page.summary or ""))
    evidence_text = re.sub(r"[^a-z0-9_-]+", " ", " ".join(evidence_parts).lower())
    covered = sum(1 for term in terms if term in evidence_text)
    return (covered / max(len(terms), 1)) >= 0.5


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
    for intent in INTENT_PRIORITY:
        patterns = INTENT_KEYWORDS[intent]
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
        "authority_check": "authority_check",
        "risk_review": "risk_review",
        "change_review": "change_review",
        "source_lookup": "source_lookup",
        "summary": "summary",
        "correction_followup": "clarified_answer",
        "analysis": "analysis",
    }.get(intent, "direct_answer")


def _is_followup_style(question: str) -> bool:
    lowered = question.strip().lower()
    return any(lowered.startswith(prefix) for prefix in FOLLOW_UP_PREFIXES)


def _planner_focus_hint(question: str, target_entities: list[str], scope_hint: str | None) -> str | None:
    if target_entities:
        return target_entities[0]
    return scope_hint


def _split_planner_clauses(question: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", question.strip())
    if not normalized:
        return []
    parts = re.split(r"\?\s*|;\s*|,\s*(?=(?:and|va|và|what|which|how|risk|rui ro|luu y|watch for|test))", normalized, flags=re.IGNORECASE)
    clauses: list[str] = []
    buffer = ""
    for part in parts:
        text = re.sub(r"\s+", " ", str(part or "")).strip(" ,;")
        if not text:
            continue
        if text.lower() in {"and", "va", "và"}:
            if buffer:
                buffer = f"{buffer} {text}"
            continue
        if len(text.split()) <= 3 and clauses:
            clauses[-1] = f"{clauses[-1]} {text}".strip()
            continue
        if buffer:
            text = f"{buffer} {text}".strip()
            buffer = ""
        clauses.append(text)
    clauses = _dedupe_keep_order([clause for clause in clauses if len(clause.split()) >= 3])
    if len(clauses) >= 2:
        first_lower = clauses[0].lower()
        actionable_markers = ("what", "how", "which", "prepare", "risk", "test", "compare", "source", "cần", "nen", "phai", "rủi ro", "rui ro")
        if not any(marker in first_lower for marker in actionable_markers):
            clauses[1] = f"{clauses[0]} {clauses[1]}".strip()
            clauses = clauses[1:]
    return clauses


def _decompose_question(question: str, target_entities: list[str], scope_hint: str | None) -> list[dict]:
    clauses = _split_planner_clauses(question)
    if len(clauses) < 2:
        return []
    focus_hint = _planner_focus_hint(question, target_entities, scope_hint)
    subqueries: list[dict] = []
    for index, clause in enumerate(clauses[:4], start=1):
        clause_intent = _detect_intent(clause)
        role = {
            "summary": "summary",
            "definition": "definition",
            "procedure": "step",
            "risk_review": "risk",
            "comparison": "comparison",
            "authority_check": "authority",
            "conflict_check": "conflict",
            "change_review": "change",
        }.get(clause_intent, "evidence")
        step_query = clause
        if focus_hint and focus_hint.lower() not in clause.lower():
            step_query = f"{focus_hint}: {clause}"
        subqueries.append(
            {
                "id": f"q{index}",
                "query": step_query,
                "intent": clause_intent,
                "role": role,
                "reason": f"Decomposed clause {index} from the original multi-part question.",
            }
        )
    return subqueries if len(subqueries) >= 2 else []


def _build_query_planner(
    trimmed: str,
    intent: str,
    recent_questions: list[str],
    target_entities: list[str],
    scope_hint: str | None,
    needs_clarification: bool,
    clarification_question: str | None,
    prefer_followup_rewrite: bool = False,
) -> dict:
    if needs_clarification:
        return {
            "strategy": "ask_back",
            "rationale": "Follow-up is too ambiguous to retrieve grounded evidence safely.",
            "askBackMode": "structured_clarification",
            "subQueries": [],
        }
    if prefer_followup_rewrite and recent_questions:
        return {
            "strategy": "followup_rewrite",
            "rationale": "Follow-up was rewritten against the active conversation focus before retrieval.",
            "askBackMode": None,
            "subQueries": [],
        }
    subqueries = _decompose_question(trimmed, target_entities, scope_hint)
    if subqueries:
        return {
            "strategy": "decompose",
            "rationale": "Question contains multiple reasoning goals, so retrieval is split into sub-queries before synthesis.",
            "askBackMode": None,
            "subQueries": subqueries,
        }
    if _is_followup_style(trimmed) and recent_questions:
        return {
            "strategy": "followup_rewrite",
            "rationale": "Follow-up is rewritten against the active conversation focus before retrieval.",
            "askBackMode": None,
            "subQueries": [],
        }
    return {
        "strategy": "single_query",
        "rationale": f"Single dominant intent detected: {intent}.",
        "askBackMode": None,
        "subQueries": [],
    }


def _build_query_understanding(
    question: str,
    recent_messages: list[ChatMessage],
    source_id: str | None = None,
    collection_id: str | None = None,
    page_id: str | None = None,
    actor=None,
) -> dict:
    trimmed = re.sub(r"\s+", " ", question.strip())
    recent_questions = _recent_user_questions(recent_messages)
    recent_entities = _extract_recent_entities(recent_messages)
    intent = _detect_intent(trimmed)
    answer_type = _answer_type_for_intent(intent)
    standalone_query = trimmed
    needs_clarification = False
    clarification_question = None
    conversation_summary = None
    followup_rewritten = False

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
                followup_rewritten = True
            else:
                needs_clarification = True
        elif any(marker in lowered for marker in ("so sánh", "so sanh")) and recent_entities:
            standalone_query = f"So sánh {' và '.join(recent_entities[:2])} trong ngữ cảnh: {last_question}"
            followup_rewritten = True
        elif any(marker in lowered for marker in ("nó", "no", "cái đó", "cai do", "cái này", "cai nay", "cái trên", "cai tren")):
            subject = recent_entities[0] if recent_entities else last_question
            standalone_query = f"{trimmed} trong ngữ cảnh của: {subject}"
            followup_rewritten = True
        elif any(marker in lowered for marker in ("trả lời sai", "tra loi sai")):
            needs_clarification = True
            clarification_question = "Phần nào trong câu trả lời trước đang sai? Hãy chỉ rõ thuật ngữ, số liệu, hoặc bước bạn muốn sửa."

    target_entities = _dedupe_keep_order(
        recent_entities
        + re.findall(r'"([^"]+)"', trimmed)
        + re.findall(r"'([^']+)'", trimmed)
    )[:6]
    if intent == "comparison" and len(target_entities) < 2:
        comparison_parts = [part.strip(" .,:;-") for part in re.split(r"\bvs\b|\bversus\b|\band\b|,|/|-", trimmed, flags=re.IGNORECASE) if len(part.strip()) > 3]
        target_entities = _dedupe_keep_order(target_entities + comparison_parts[:3])[:6]
    filters = {}
    if source_id:
        filters["source_id"] = source_id
    if collection_id:
        filters["collection_id"] = collection_id
    if page_id:
        filters["page_id"] = page_id
    planner = _build_query_planner(
        standalone_query,
        intent,
        recent_questions,
        target_entities,
        None,
        needs_clarification,
        clarification_question,
        prefer_followup_rewrite=followup_rewritten,
    )
    if planner.get("strategy") == "decompose":
        intent = "analysis"
        answer_type = _answer_type_for_intent(intent)

    return {
        "standaloneQuery": standalone_query,
        "intent": intent,
        "answerType": answer_type,
        "targetEntities": target_entities,
        "filters": filters,
        "needsClarification": needs_clarification,
        "clarificationQuestion": clarification_question,
        "conversationSummary": conversation_summary,
        "planner": planner,
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
        "effectiveDate": str(metadata.get("effectiveDate") or metadata.get("effective_date") or "") or None,
        "version": str(metadata.get("version") or "") or None,
    }


def _source_authority_summary(source: Source, diagnostics: dict | None = None) -> str:
    metadata = source.metadata_json or {}
    status = str(metadata.get("sourceStatus") or metadata.get("source_status") or "unknown")
    authority = str(metadata.get("authorityLevel") or metadata.get("authority_level") or source.trust_level or "unknown")
    effective_date = str(metadata.get("effectiveDate") or metadata.get("effective_date") or "").strip()
    version = str(metadata.get("version") or "").strip()
    parts = [authority, status]
    if effective_date:
        parts.append(f"effective {effective_date}")
    if version:
        parts.append(f"version {version}")
    if diagnostics and diagnostics.get("authorityScore") is not None:
        parts.append(f"authority score {diagnostics.get('authorityScore')}")
    return ", ".join(parts)


def _metadata_match_score(
    intent: str,
    collection_id: str | None,
    source_id: str | None = None,
    page_id: str | None = None,
    source: Source | None = None,
    page: Page | None = None,
) -> float:
    score = 0.0
    if source_id and source and source.id == source_id:
        score += 0.18
    if collection_id:
        if source and source.collection_id == collection_id:
            score += 0.08
        if page and page.collection_id == collection_id:
            score += 0.08
    if page_id and page and page.id == page_id:
        score += 0.18
    source_metadata = source.metadata_json or {} if source else {}
    document_type = str(source_metadata.get("documentType") or source_metadata.get("document_type") or "").lower()
    if intent == "policy_rule" and source and (source.source_type in {"pdf", "docx", "markdown"} or document_type == "policy"):
        score += 0.04
    if intent == "procedure" and source and (source.source_type in {"docx", "markdown", "transcript"} or document_type == "sop"):
        score += 0.04
    if intent in {"definition", "summary"} and page:
        score += 0.03
    return round(score, 6)


def _resolve_scope_summary(
    db: Session,
    source_id: str | None = None,
    collection_id: str | None = None,
    page_id: str | None = None,
) -> dict | None:
    if source_id:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return None
        return {
            "type": "source",
            "id": source.id,
            "title": source.title,
            "description": source.description,
            "strict": True,
            "matchedInScope": True,
        }
    if page_id:
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            return None
        return {
            "type": "page",
            "id": page.id,
            "title": page.title,
            "description": page.summary,
            "strict": True,
            "matchedInScope": True,
        }
    if collection_id:
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            return None
        return {
            "type": "collection",
            "id": collection.id,
            "title": collection.name,
            "description": collection.description,
            "strict": True,
            "matchedInScope": True,
        }
    return None


def _prompt_texts_for_document_type(document_type: str, scope_label: str | None = None) -> list[tuple[str, str, str]]:
    label = scope_label or "this material"
    mapping = {
        "policy": [
            (f"What rules in {label} are mandatory?", "policy", "Extract the binding rules first."),
            (f"What exceptions or caveats appear in {label}?", "exception", "Look for exception handling in policy text."),
            (f"Which source in {label} is most authoritative?", "authority", "Resolve policy priority explicitly."),
        ],
        "sop": [
            (f"What are the prerequisite steps in {label}?", "procedure", "Start from prerequisites before main steps."),
            (f"Turn {label} into a checklist.", "procedure", "Convert procedure evidence into an operational checklist."),
            (f"What failure points or rollback notes appear in {label}?", "risk", "Surface operational risk early."),
        ],
        "report": [
            (f"Summarize the main recommendation in {label}.", "summary", "Focus on decision-ready summary."),
            (f"What risks or tradeoffs are called out in {label}?", "risk", "Highlight risks and tradeoffs."),
            (f"What evidence supports the recommendation in {label}?", "evidence", "Trace recommendation back to evidence."),
        ],
        "glossary": [
            (f"What are the key terms defined in {label}?", "definition", "Use the document as a definition source."),
            (f"Which term in {label} matters most for this topic?", "definition", "Drive follow-up from glossary context."),
        ],
    }
    return mapping.get(document_type, [])


def _document_type_from_scope(db: Session, scope: dict | None) -> str | None:
    if not scope:
        return None
    if scope["type"] == "source":
        source = db.query(Source).filter(Source.id == scope["id"]).first()
        if source:
            metadata = source.metadata_json or {}
            return str(metadata.get("documentType") or metadata.get("document_type") or "").lower() or None
    if scope["type"] == "page":
        page = db.query(Page).filter(Page.id == scope["id"]).first()
        if page:
            return str(page.page_type or "").lower() or None
    return None


def _notebook_context_items(source: Source) -> list[dict]:
    metadata = source.metadata_json or {}
    notebook_context = metadata.get("notebookContext") or {}
    items: list[dict] = []
    brief = str(notebook_context.get("sourceBrief") or "").strip()
    if brief:
        items.append(
            {
                "id": f"{source.id}:source-brief",
                "kind": "source_brief",
                "title": "Source Brief",
                "text": brief,
                "roles": ["summary"],
                "provenance": {"sourceId": source.id, "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
            }
        )
    for note in notebook_context.get("notes") or []:
        if not isinstance(note, dict):
            continue
        text = str(note.get("text") or "").strip()
        if not text:
            continue
        items.append(
            {
                "id": str(note.get("id") or f"{source.id}:note:{len(items)}"),
                "kind": str(note.get("kind") or "grouped_note"),
                "title": str(note.get("title") or "Notebook Note"),
                "text": text,
                "roles": [str(role).lower() for role in (note.get("roles") or []) if str(role).strip()],
                "provenance": note.get("provenance") or {"sourceId": source.id, "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
            }
        )
    return items


def _dedupe_prompt_payloads(items: list[tuple[str, str, str | None]], limit: int = 6) -> list[dict]:
    seen: set[str] = set()
    prompts: list[dict] = []
    for text, category, reason in items:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        prompts.append({"text": normalized, "category": category, "reason": reason})
        if len(prompts) >= limit:
            break
    return prompts


def _build_suggested_prompts(
    db: Session,
    question: str,
    interpreted: dict,
    scope: dict | None,
    selected_candidates: list[dict],
    conflicts: list[dict],
    uncertainty: str | None,
) -> list[dict]:
    prompts: list[tuple[str, str, str | None]] = []
    scope_label = scope["title"] if scope else "the knowledge base"
    scope_phrase = (
        f"this {scope['type']}" if scope else "the current knowledge base"
    )
    document_type = _document_type_from_scope(db, scope)
    intent = interpreted.get("intent") or "fact_lookup"

    if uncertainty:
        prompts.extend(
            [
                (f"Summarize {scope_label}.", "summary", "Use a scoped summary to narrow the next answer."),
                (f"What exact section in {scope_label} mentions this topic?", "clarify", "Ask for section-level grounding."),
                (f"Which source should I open first to answer this question?", "source_lookup", "Recover by locating the best source first."),
            ]
        )

    if conflicts:
        prompts.extend(
            [
                ("Which source should be trusted more here, and why?", "authority", "Resolve priority across conflicting evidence."),
                ("What exact conflict exists between the cited sources?", "conflict", "Explain the conflict directly."),
            ]
        )

    prompts.extend(_prompt_texts_for_document_type(document_type or "", scope_label))

    if not uncertainty:
        prompts.extend(
            [
                (f"Show the strongest evidence for this answer in {scope_phrase}.", "evidence", "Inspect the top supporting evidence."),
                ("Turn this answer into a short checklist.", "procedure", "Convert grounded evidence into action steps."),
            ]
        )

    if intent in {"summary", "fact_lookup", "definition"}:
        prompts.extend(
            [
                (f"What are the most important points in {scope_label}?", "summary", "Drive a notebook-style summary."),
                (f"What terminology or definitions matter most here?", "definition", "Follow up with key terms."),
            ]
        )
    elif intent in {"procedure", "threshold", "policy_rule"}:
        prompts.extend(
            [
                ("What prerequisites should be checked before doing this?", "procedure", "Surface prerequisite steps."),
                ("Are there exceptions, thresholds, or approvals to watch for?", "risk", "Look for policy exceptions and limits."),
            ]
        )
    elif intent in {"comparison", "conflict_check", "change_review"}:
        prompts.extend(
            [
                ("Summarize the differences source by source.", "comparison", "Break the comparison down by source."),
                ("What is the safer operational interpretation?", "authority", "Translate conflict into a usable decision."),
            ]
        )
        if intent == "change_review":
            prompts.extend(
                [
                    ("What changed between the current and previous guidance?", "change_review", "Focus the next step on version-aware differences."),
                    ("Which changes affect approvals, thresholds, or exceptions most?", "change_review", "Highlight operationally important deltas."),
                ]
            )
    elif intent in {"risk_review", "analysis"}:
        prompts.extend(
            [
                ("What should be prepared first before acting on this?", "procedure", "Convert analysis into next steps."),
                ("What risks or caveats deserve attention first?", "risk", "Keep the follow-up grounded on operational risk."),
            ]
        )

    if scope and scope["type"] == "source":
        prompts.extend(
            [
                (f"Summarize {scope_label} for a quick handoff.", "summary", "Notebook-style source brief."),
                (f"What sections in {scope_label} should I read first?", "source_lookup", "Guide the next source read."),
            ]
        )
    elif scope and scope["type"] == "collection":
        prompts.extend(
            [
                (f"Which document in {scope_label} is most authoritative for this topic?", "authority", "Select the right document in the collection."),
                (f"Compare the top two relevant documents in {scope_label}.", "comparison", "Drive multi-document synthesis."),
            ]
        )
    elif scope and scope["type"] == "page":
        prompts.extend(
            [
                (f"What source evidence backs this page most strongly?", "evidence", "Trace page content back to sources."),
                (f"What parts of {scope_label} may be stale or need review?", "risk", "Prompt review-oriented follow-up."),
            ]
        )

    if not scope:
        prompts.extend(
            [
                ("Should I narrow this to a specific source or collection first?", "scope", "Reduce retrieval drift by scoping the question."),
                ("Which source is the best starting point for this topic?", "source_lookup", "Find the best source before deeper reasoning."),
            ]
        )

    if selected_candidates:
        top = selected_candidates[0]
        source = top.get("source")
        if source:
            prompts.append((f"Summarize {source.title} only.", "scope", "Lock the next answer to the strongest source."))

    return _dedupe_prompt_payloads(prompts, limit=6)


def _scoped_ids(db: Session, filters: dict) -> tuple[set[str] | None, set[str] | None]:
    source_id = filters.get("source_id")
    page_id = filters.get("page_id")
    if source_id:
        page_ids = {
            linked_page_id
            for (linked_page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id == source_id).all()
        }
        return {source_id}, page_ids
    if page_id:
        source_ids = {
            linked_source_id
            for (linked_source_id,) in db.query(PageSourceLink.source_id).filter(PageSourceLink.page_id == page_id).all()
        }
        return source_ids or set(), {page_id}
    return None, None


def _resolve_explicit_source_ids(
    db: Session,
    interpreted: dict,
    scoped_source_ids: set[str] | None,
    collection_id: str | None,
) -> set[str]:
    candidate_entities = [str(entity).strip() for entity in (interpreted.get("targetEntities") or []) if str(entity).strip()]
    candidate_entities = [entity for entity in candidate_entities if len(entity.split()) >= 2]
    standalone_query = str(interpreted.get("standaloneQuery") or "").strip().lower()
    if not candidate_entities:
        candidate_entities = []
    source_query = db.query(Source)
    if scoped_source_ids is not None:
        if not scoped_source_ids:
            return set()
        source_query = source_query.filter(Source.id.in_(list(scoped_source_ids)))
    if collection_id:
        source_query = source_query.filter(Source.collection_id == collection_id)
    matches: set[str] = set()
    for source in source_query.all():
        title = (source.title or "").strip().lower()
        if not title:
            continue
        if standalone_query and title in standalone_query:
            matches.add(source.id)
            continue
        for entity in candidate_entities:
            lowered = entity.lower()
            if lowered in title or title in lowered:
                matches.add(source.id)
                break
    return matches


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


def _artifact_summary_text(artifact: dict) -> str:
    metadata = artifact.get("metadataJson") if isinstance(artifact.get("metadataJson"), dict) else {}
    artifact_type = str(artifact.get("artifactType") or "").lower()
    lines = [
        str(artifact.get("title") or "").strip(),
        str(artifact.get("summary") or "").strip(),
        str(artifact.get("previewText") or "").strip(),
    ]
    if artifact_type == "structure":
        section_summaries = metadata.get("sectionSummaries") if isinstance(metadata.get("sectionSummaries"), list) else []
        section_titles = [str(item.get("title") or "").strip() for item in section_summaries[:6] if isinstance(item, dict)]
        lines.append("Sections: " + ", ".join(title for title in section_titles if title))
    elif artifact_type == "notebook":
        prompts = metadata.get("recommendedPrompts") if isinstance(metadata.get("recommendedPrompts"), list) else []
        lines.append("Prompts: " + " | ".join(str(prompt).strip() for prompt in prompts[:4] if str(prompt).strip()))
    elif artifact_type == "table":
        ordered_block = metadata.get("orderedBlock") if isinstance(metadata.get("orderedBlock"), dict) else {}
        lines.append(str(ordered_block.get("content") or "").strip())
    elif artifact_type == "ocr":
        languages = metadata.get("ocrLanguages") if isinstance(metadata.get("ocrLanguages"), list) else []
        lines.append("OCR languages: " + ", ".join(str(language).strip() for language in languages if str(language).strip()))
    elif artifact_type == "image":
        lines.append(str(metadata.get("contextBefore") or "").strip())
    return "\n".join(line for line in lines if line).strip()


def _artifact_role_tags(artifact: dict) -> list[str]:
    artifact_type = str(artifact.get("artifactType") or "").lower()
    tags = [artifact_type] if artifact_type else []
    if artifact_type in {"structure", "notebook"}:
        tags.extend(["summary", "evidence"])
    elif artifact_type in {"table", "ocr"}:
        tags.extend(["evidence", "detail"])
    elif artifact_type == "image":
        tags.extend(["detail", "visual"])
    return _dedupe_keep_order(tags)


def _diagnostic_candidates(candidates: list[dict], interpreted: dict, limit: int) -> list[dict]:
    if not candidates:
        return []
    intent = interpreted.get("intent") or "fact_lookup"
    if intent in {"comparison", "conflict_check", "authority_check", "analysis", "change_review", "source_lookup"}:
        return candidates[:limit]
    best_score = float(candidates[0].get("rerank_score", candidates[0].get("score", 0.0)) or 0.0)
    minimum_competitive_score = best_score * 0.9 if best_score > 0 else 0.0
    filtered: list[dict] = []
    seen_other_sources: set[str] = set()
    top_source = candidates[0].get("source").id if candidates[0].get("source") else None
    for candidate in candidates:
        source = candidate.get("source")
        source_id = source.id if source else None
        candidate_score = float(candidate.get("rerank_score", candidate.get("score", 0.0)) or 0.0)
        if source_id and top_source and source_id != top_source and candidate_score < minimum_competitive_score:
            continue
        if source_id and top_source and source_id != top_source:
            if source_id in seen_other_sources:
                continue
            seen_other_sources.add(source_id)
        filtered.append(candidate)
        if len(filtered) >= limit:
            break
    return filtered


def _retrieval_policy(intent: str) -> dict:
    policies = {
        "definition": {
            "preferred_types": ["claim", "chunk", "knowledge_unit", "notebook_note", "artifact_summary", "section_summary", "page_summary"],
            "desired_roles": ["evidence", "definition", "summary", "detail"],
        },
        "procedure": {
            "preferred_types": ["notebook_note", "artifact_summary", "knowledge_unit", "section_summary", "chunk", "claim", "page_summary"],
            "desired_roles": ["step", "exception", "evidence"],
        },
        "policy_rule": {
            "preferred_types": ["notebook_note", "artifact_summary", "knowledge_unit", "claim", "section_summary", "chunk", "page_summary"],
            "desired_roles": ["evidence", "exception", "summary"],
        },
        "comparison": {
            "preferred_types": ["notebook_note", "artifact_summary", "knowledge_unit", "claim", "section_summary", "chunk", "page_summary"],
            "desired_roles": ["comparison_a", "comparison_b", "summary"],
        },
        "conflict_check": {
            "preferred_types": ["notebook_note", "artifact_summary", "claim", "knowledge_unit", "section_summary", "chunk", "page_summary"],
            "desired_roles": ["evidence", "conflict_side_a", "conflict_side_b"],
        },
        "authority_check": {
            "preferred_types": ["notebook_note", "artifact_summary", "claim", "knowledge_unit", "section_summary", "page_summary", "chunk"],
            "desired_roles": ["evidence", "summary", "detail"],
        },
        "threshold": {
            "preferred_types": ["notebook_note", "artifact_summary", "knowledge_unit", "claim", "section_summary", "chunk", "page_summary"],
            "desired_roles": ["evidence", "exception", "detail"],
        },
        "risk_review": {
            "preferred_types": ["notebook_note", "artifact_summary", "section_summary", "knowledge_unit", "chunk", "claim", "page_summary"],
            "desired_roles": ["exception", "evidence", "summary"],
        },
        "change_review": {
            "preferred_types": ["notebook_note", "artifact_summary", "section_summary", "page_summary", "knowledge_unit", "claim", "chunk"],
            "desired_roles": ["comparison_a", "comparison_b", "summary"],
        },
        "summary": {
            "preferred_types": ["notebook_note", "artifact_summary", "page_summary", "section_summary", "knowledge_unit", "claim", "chunk"],
            "desired_roles": ["summary", "evidence", "detail"],
        },
        "source_lookup": {
            "preferred_types": ["notebook_note", "artifact_summary", "section_summary", "chunk", "claim", "knowledge_unit", "page_summary"],
            "desired_roles": ["evidence", "detail", "summary"],
        },
        "analysis": {
            "preferred_types": ["notebook_note", "artifact_summary", "section_summary", "knowledge_unit", "chunk", "claim", "page_summary"],
            "desired_roles": ["summary", "step", "exception", "evidence"],
        },
    }
    default_policy = {
        "preferred_types": ["notebook_note", "artifact_summary", "knowledge_unit", "claim", "section_summary", "chunk", "page_summary"],
        "desired_roles": ["evidence", "detail", "summary"],
    }
    policy = dict(policies.get(intent, default_policy))
    preferred_types = list(policy["preferred_types"])
    if "user_note" not in preferred_types:
        insert_at = preferred_types.index("notebook_note") + 1 if "notebook_note" in preferred_types else 0
        preferred_types.insert(insert_at, "user_note")
    policy["preferred_types"] = preferred_types
    return policy


def _has_grounded_scope_match(candidates: list[dict]) -> bool:
    for candidate in candidates:
        diagnostics = candidate.get("diagnostics") or {}
        if float(diagnostics.get("lexicalScore") or 0.0) >= 0.2:
            return True
        if float(diagnostics.get("titleBonus") or 0.0) >= 0.1:
            return True
    return False


def _retrieve_candidates_for_query(
    db: Session,
    runtime,
    interpreted: dict,
    query_embedding: list[float] | None,
    question: str | None = None,
    intent_override: str | None = None,
    planner_step: dict | None = None,
    actor=None,
) -> list[dict]:
    question = question or interpreted["standaloneQuery"]
    intent = intent_override or interpreted["intent"]
    filters = interpreted.get("filters", {})
    source_id = filters.get("source_id")
    collection_id = filters.get("collection_id")
    page_id = filters.get("page_id")
    scoped_source_ids, scoped_page_ids = _scoped_ids(db, filters)
    explicit_source_ids = _resolve_explicit_source_ids(db, interpreted, scoped_source_ids, collection_id)
    terms = _query_terms(question)
    candidates: list[dict] = []

    chunk_query = _searchable_source_filter(db.query(SourceChunk, Source).join(Source, SourceChunk.source_id == Source.id))
    if scoped_source_ids is not None:
        if not scoped_source_ids:
            chunk_query = chunk_query.filter(Source.id == "__no_source_scope__")
        else:
            chunk_query = chunk_query.filter(Source.id.in_(list(scoped_source_ids)))
    if explicit_source_ids:
        chunk_query = chunk_query.filter(Source.id.in_(list(explicit_source_ids)))
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
        metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
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
                    "plannerStepId": planner_step.get("id") if planner_step else None,
                    "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                    "plannerStepRole": planner_step.get("role") if planner_step else None,
                    "diagnostics": diagnostics,
                }
            )

    if actor is not None:
        note_query = (
            db.query(Note, NoteAnchor, Source)
            .join(NoteAnchor, NoteAnchor.note_id == Note.id)
            .join(Source, NoteAnchor.source_id == Source.id)
            .filter(Note.status == "active")
        )
        visibility_filters = [Note.scope == "workspace"]
        if getattr(actor, "id", None):
            visibility_filters.append(Note.owner_id == actor.id)
        if getattr(actor, "collection_scope_mode", "all") == "restricted":
            accessible = list(getattr(actor, "accessible_collection_ids", ()) or [])
            if accessible:
                visibility_filters.append(Note.collection_id.in_(accessible))
        else:
            visibility_filters.append(Note.scope == "collection")
        note_query = note_query.filter(or_(*visibility_filters))
        if scoped_source_ids is not None:
            if not scoped_source_ids:
                note_query = note_query.filter(Source.id == "__no_source_scope__")
            else:
                note_query = note_query.filter(Source.id.in_(list(scoped_source_ids)))
        if explicit_source_ids:
            note_query = note_query.filter(Source.id.in_(list(explicit_source_ids)))
        if collection_id:
            note_query = note_query.filter(Note.collection_id == collection_id)
        if terms:
            note_filters = []
            for term in terms[:8]:
                like = f"%{term}%"
                note_filters.extend([Note.title.ilike(like), Note.body.ilike(like), NoteAnchor.snippet.ilike(like), Source.title.ilike(like)])
            note_query = note_query.filter(or_(*note_filters))
        for note, anchor, source in note_query.limit(max(runtime.retrieval_limit * 8, 50)).all():
            if not can_access_collection_id(actor, source.collection_id):
                continue
            text = f"{note.title}\n{note.body}\n{anchor.snippet}"
            diagnostics = _score_components(question, text, f"{source.title} {note.title}", runtime.hybrid_semantic_weight, query_embedding)
            metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
            final = diagnostics["finalScore"] + metadata_score + 0.04
            diagnostics.update({"metadataScore": round(metadata_score, 6), "finalScore": round(final, 6)})
            if final > 0:
                candidates.append(
                    {
                        "type": "user_note",
                        "id": note.id,
                        "score": final,
                        "source": source,
                        "chunk": None,
                        "page": None,
                        "claim": None,
                        "note": note,
                        "note_anchor": anchor,
                        "text": text,
                        "excerpt": (anchor.snippet or note.body)[:220],
                        "plannerStepId": planner_step.get("id") if planner_step else None,
                        "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                        "plannerStepRole": planner_step.get("role") if planner_step else None,
                        "diagnostics": diagnostics,
                    }
                )

    claim_query = _searchable_source_filter(db.query(Claim, SourceChunk, Source).join(SourceChunk, Claim.source_chunk_id == SourceChunk.id).join(Source, SourceChunk.source_id == Source.id))
    if scoped_source_ids is not None:
        if not scoped_source_ids:
            claim_query = claim_query.filter(Source.id == "__no_source_scope__")
        else:
            claim_query = claim_query.filter(Source.id.in_(list(scoped_source_ids)))
    if explicit_source_ids:
        claim_query = claim_query.filter(Source.id.in_(list(explicit_source_ids)))
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
        metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
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
                    "plannerStepId": planner_step.get("id") if planner_step else None,
                    "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                    "plannerStepRole": planner_step.get("role") if planner_step else None,
                    "diagnostics": diagnostics,
                }
            )

    knowledge_query = _searchable_source_filter(db.query(KnowledgeUnit, Source).join(Source, KnowledgeUnit.source_id == Source.id))
    if scoped_source_ids is not None:
        if not scoped_source_ids:
            knowledge_query = knowledge_query.filter(Source.id == "__no_source_scope__")
        else:
            knowledge_query = knowledge_query.filter(Source.id.in_(list(scoped_source_ids)))
    if explicit_source_ids:
        knowledge_query = knowledge_query.filter(Source.id.in_(list(explicit_source_ids)))
    if collection_id:
        knowledge_query = knowledge_query.filter(Source.collection_id == collection_id)
    if terms:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([KnowledgeUnit.title.ilike(like), KnowledgeUnit.text.ilike(like), KnowledgeUnit.topic.ilike(like), Source.title.ilike(like)])
        knowledge_query = knowledge_query.filter(or_(*filters))
    for unit, source in knowledge_query.limit(max(runtime.retrieval_limit * 10, 80)).all():
        text = f"{unit.title}\n{unit.text}\n{unit.topic or ''}"
        diagnostics = _score_components(question, text, unit.title or source.title, runtime.hybrid_semantic_weight)
        metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
        authority_total, authority_details = _source_priority(source)
        verification_boost = 0.05 if unit.review_status == "approved" or unit.canonical_status == "verified" else 0.0
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
                    "type": "knowledge_unit",
                    "id": unit.id,
                    "score": final,
                    "source": source,
                    "chunk": None,
                    "page": None,
                    "claim": None,
                    "knowledge_unit": unit,
                    "text": text,
                    "excerpt": unit.text[:220],
                    "plannerStepId": planner_step.get("id") if planner_step else None,
                    "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                    "plannerStepRole": planner_step.get("role") if planner_step else None,
                    "diagnostics": diagnostics,
                }
            )

    source_query = _searchable_source_filter(db.query(Source))
    strict_source_scope = bool(source_id or explicit_source_ids or scoped_source_ids is not None)
    if scoped_source_ids is not None:
        if not scoped_source_ids:
            source_query = source_query.filter(Source.id == "__no_source_scope__")
        else:
            source_query = source_query.filter(Source.id.in_(list(scoped_source_ids)))
    if explicit_source_ids:
        source_query = source_query.filter(Source.id.in_(list(explicit_source_ids)))
    if collection_id:
        source_query = source_query.filter(Source.collection_id == collection_id)
    if terms and not strict_source_scope:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([Source.title.ilike(like), Source.description.ilike(like)])
        source_query = source_query.filter(or_(*filters))
    for source in source_query.limit(max(runtime.retrieval_limit * 6, 40)).all():
        multimodal_artifacts = (source.metadata_json or {}).get("multimodalArtifacts")
        if isinstance(multimodal_artifacts, list):
            for artifact in multimodal_artifacts[:18]:
                if not isinstance(artifact, dict):
                    continue
                artifact_type = str(artifact.get("artifactType") or "").lower()
                if artifact_type not in {"structure", "notebook", "table", "ocr", "image"}:
                    continue
                text = _artifact_summary_text(artifact)
                if not text:
                    continue
                diagnostics = _score_components(
                    question,
                    text,
                    f"{source.title} {artifact.get('title') or artifact_type}",
                    runtime.hybrid_semantic_weight,
                )
                metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
                authority_total, authority_details = _source_priority(source)
                artifact_bonus = 0.0
                if artifact_type in {"structure", "notebook"}:
                    artifact_bonus += 0.05
                elif artifact_type in {"table", "ocr"}:
                    artifact_bonus += 0.03
                final = diagnostics["finalScore"] + metadata_score + authority_total + artifact_bonus
                diagnostics.update({
                    "metadataScore": round(metadata_score + artifact_bonus, 6),
                    "authorityScore": round(authority_total, 6),
                    "finalScore": round(final, 6),
                    **authority_details,
                })
                if final <= 0:
                    continue
                candidates.append(
                    {
                        "type": "artifact_summary",
                        "id": str(artifact.get("id") or f"{source.id}-{artifact_type}"),
                        "score": final,
                        "source": source,
                        "chunk": None,
                        "page": None,
                        "claim": None,
                        "artifact": artifact,
                        "text": text,
                        "excerpt": text[:220],
                        "plannerStepId": planner_step.get("id") if planner_step else None,
                        "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                        "plannerStepRole": planner_step.get("role") if planner_step else None,
                        "diagnostics": diagnostics,
                    }
                )
        note_items = _notebook_context_items(source)
        for note in note_items[:16]:
            text = f"{note['title']}\n{note['text']}\n{' '.join(note.get('roles') or [])}"
            diagnostics = _score_components(question, text, f"{source.title} {note['title']}", runtime.hybrid_semantic_weight)
            metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
            authority_total, authority_details = _source_priority(source)
            role_bonus = 0.06 if any(role in {"summary", "step", "exception", "evidence"} for role in (note.get("roles") or [])) else 0.0
            final = diagnostics["finalScore"] + metadata_score + authority_total + role_bonus
            diagnostics.update({
                "metadataScore": round(metadata_score + role_bonus, 6),
                "authorityScore": round(authority_total, 6),
                "finalScore": round(final, 6),
                **authority_details,
            })
            if final > 0:
                provenance = note.get("provenance") or {}
                chunk_id = next((str(item) for item in (provenance.get("chunkIds") or []) if str(item).strip()), None)
                linked_chunk = db.query(SourceChunk).filter(SourceChunk.id == chunk_id).first() if chunk_id else None
                candidates.append(
                    {
                        "type": "notebook_note",
                        "id": str(note["id"]),
                        "score": final,
                        "source": source,
                        "chunk": linked_chunk,
                        "page": None,
                        "claim": None,
                        "notebook_note": note,
                        "text": text,
                        "excerpt": str(note["text"])[:220],
                        "provenanceChunkId": chunk_id,
                        "plannerStepId": planner_step.get("id") if planner_step else None,
                        "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                        "plannerStepRole": planner_step.get("role") if planner_step else None,
                        "diagnostics": diagnostics,
                    }
                )
        section_summaries = list((source.metadata_json or {}).get("sectionSummaries") or [])
        for section in section_summaries[:24]:
            section_title = str(section.get("title") or "Document")
            section_summary = str(section.get("summary") or "").strip()
            if not section_summary:
                continue
            role_text = " ".join(str(role) for role in (section.get("roles") or []))
            text = f"{section_title}\n{section_summary}\n{role_text}"
            diagnostics = _score_components(question, text, f"{source.title} {section_title}", runtime.hybrid_semantic_weight)
            metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, source=source)
            authority_total, authority_details = _source_priority(source)
            role_bonus = 0.05 if intent == "procedure" and any(role in {"step", "prerequisite", "exception"} for role in (section.get("roles") or [])) else 0.04 if intent in {"policy_rule", "threshold"} and any(role in {"rule", "scope", "exception"} for role in (section.get("roles") or [])) else 0.0
            final = diagnostics["finalScore"] + metadata_score + authority_total + role_bonus
            diagnostics.update({
                "metadataScore": round(metadata_score + role_bonus, 6),
                "authorityScore": round(authority_total, 6),
                "finalScore": round(final, 6),
                **authority_details,
            })
            if final > 0:
                candidates.append(
                    {
                        "type": "section_summary",
                        "id": str(section.get("sectionKey") or f"{source.id}:{section_title}"),
                        "score": final,
                        "source": source,
                        "chunk": None,
                        "page": None,
                        "claim": None,
                        "section_summary": section,
                        "text": text,
                        "excerpt": section_summary[:220],
                        "plannerStepId": planner_step.get("id") if planner_step else None,
                        "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                        "plannerStepRole": planner_step.get("role") if planner_step else None,
                        "diagnostics": diagnostics,
                    }
                )

    page_query = (
        _searchable_source_filter(
            db.query(Page)
            .join(PageSourceLink, PageSourceLink.page_id == Page.id)
            .join(Source, PageSourceLink.source_id == Source.id)
        )
    )
    if scoped_page_ids is not None:
        if not scoped_page_ids:
            page_query = page_query.filter(Page.id == "__no_page_scope__")
        else:
            page_query = page_query.filter(Page.id.in_(list(scoped_page_ids)))
    if collection_id:
        page_query = page_query.filter(Page.collection_id == collection_id)
    page_query = page_query.filter(Page.status.in_(SEARCHABLE_PAGE_STATUSES))
    if terms:
        filters = []
        for term in terms[:8]:
            like = f"%{term}%"
            filters.extend([Page.title.ilike(like), Page.summary.ilike(like), Page.content_md.ilike(like)])
        page_query = page_query.filter(or_(*filters))
    for page in page_query.limit(max(runtime.retrieval_limit * 8, 60)).all():
        text = f"{page.title}\n{page.summary}\n{page.content_md[:1200]}"
        diagnostics = _score_components(question, text, page.title, runtime.hybrid_semantic_weight)
        metadata_score = _metadata_match_score(intent, collection_id, source_id=source_id, page_id=page_id, page=page)
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
                    "plannerStepId": planner_step.get("id") if planner_step else None,
                    "plannerStepIntent": planner_step.get("intent") if planner_step else intent,
                    "plannerStepRole": planner_step.get("role") if planner_step else None,
                    "diagnostics": diagnostics,
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def _merge_planned_candidates(candidates: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str], dict] = {}
    for candidate in candidates:
        key = (candidate["type"], candidate["id"])
        existing = merged.get(key)
        if existing is None or candidate["score"] > existing["score"]:
            payload = dict(candidate)
            payload["planningStepIds"] = [step_id for step_id in [candidate.get("plannerStepId")] if step_id]
            payload["planningStepIntents"] = [step_intent for step_intent in [candidate.get("plannerStepIntent")] if step_intent]
            payload["planningStepRoles"] = [step_role for step_role in [candidate.get("plannerStepRole")] if step_role]
            merged[key] = payload
            continue
        for step_id in [candidate.get("plannerStepId")]:
            if step_id and step_id not in existing.setdefault("planningStepIds", []):
                existing["planningStepIds"].append(step_id)
        for step_intent in [candidate.get("plannerStepIntent")]:
            if step_intent and step_intent not in existing.setdefault("planningStepIntents", []):
                existing["planningStepIntents"].append(step_intent)
        for step_role in [candidate.get("plannerStepRole")]:
            if step_role and step_role not in existing.setdefault("planningStepRoles", []):
                existing["planningStepRoles"].append(step_role)
        existing["score"] = max(existing["score"], candidate["score"])
        existing["diagnostics"]["finalScore"] = round(max(float(existing["diagnostics"].get("finalScore") or 0.0), float(candidate["diagnostics"].get("finalScore") or 0.0)), 6)
    for item in merged.values():
        planning_intents = item.get("planningStepIntents") or []
        planning_roles = item.get("planningStepRoles") or []
        if "risk_review" in planning_intents:
            item["plannerStepIntent"] = "risk_review"
        elif planning_intents:
            item["plannerStepIntent"] = planning_intents[0]
        if "risk" in planning_roles:
            item["plannerStepRole"] = "risk"
        elif planning_roles:
            item["plannerStepRole"] = planning_roles[0]
    return sorted(merged.values(), key=lambda item: item["score"], reverse=True)


def _retrieve_candidates(
    db: Session,
    runtime,
    interpreted: dict,
    query_embedding: list[float] | None,
    query_variants: list[dict] | None = None,
    actor=None,
) -> list[dict]:
    return retrieve_candidates(
        db=db,
        runtime=runtime,
        interpreted=interpreted,
        query_embedding=query_embedding,
        actor=actor,
        single_query_retriever=_retrieve_candidates_for_query,
        planned_candidate_merger=_merge_planned_candidates,
        query_embedder=_embed_query,
        query_variants=query_variants,
    )


def _rerank_candidates(candidates: list[dict], interpreted: dict, limit: int = 12) -> list[dict]:
    intent = interpreted["intent"]
    target_entities = [entity.lower() for entity in interpreted.get("targetEntities", [])]
    content_terms = _content_query_terms(interpreted.get("standaloneQuery") or "")
    reranked: list[dict] = []
    for index, candidate in enumerate(candidates[:limit]):
        candidate_intent = str(candidate.get("plannerStepIntent") or intent)
        policy = _retrieval_policy(candidate_intent)
        bonus = 0.0
        reasons: list[str] = []
        text_lower = (candidate.get("text") or "").lower()
        section_roles = [str(role).lower() for role in ((candidate.get("section_summary") or {}).get("roles") or [])]
        note_roles = [str(role).lower() for role in ((candidate.get("notebook_note") or {}).get("roles") or [])]
        artifact = candidate.get("artifact") or {}
        artifact_type = str(artifact.get("artifactType") or "").lower()
        artifact_tags = _artifact_role_tags(artifact) if artifact else []
        chunk = candidate.get("chunk")
        chunk_section_role = str(((chunk.metadata_json or {}) if chunk else {}).get("sectionRole") or "").lower()
        if candidate["type"] in policy["preferred_types"]:
            rank = policy["preferred_types"].index(candidate["type"])
            type_bonus = max(0.01, 0.08 - (rank * 0.015))
            bonus += type_bonus
            reasons.append(f"intent_type_pref:{candidate_intent}:{candidate['type']}")
        if target_entities and any(entity in text_lower for entity in target_entities):
            bonus += 0.08
            reasons.append("entity_match")
        if content_terms:
            overlap_count = sum(1 for term in content_terms if term in text_lower)
            if overlap_count == 0:
                bonus -= 0.12
                reasons.append("no_content_term_overlap")
            elif overlap_count == 1 and len(content_terms) >= 2:
                bonus -= 0.12
                reasons.append("thin_content_term_overlap")
            elif overlap_count >= 2:
                bonus += 0.05
                reasons.append("strong_content_term_overlap")
        if candidate_intent == "definition" and candidate["type"] in {"page_summary", "claim", "section_summary", "knowledge_unit"}:
            bonus += 0.07
            reasons.append("definition_surface")
        elif candidate_intent == "definition" and candidate["type"] == "notebook_note" and any(role in {"summary", "definition", "evidence"} for role in note_roles):
            bonus += 0.09
            reasons.append("definition_notebook")
        elif candidate_intent == "definition" and candidate["type"] == "artifact_summary" and artifact_type in {"structure", "notebook"}:
            bonus += 0.08
            reasons.append("definition_artifact")
        elif candidate_intent == "procedure" and candidate["type"] == "chunk":
            bonus += 0.08
            reasons.append("procedure_chunk")
            if chunk_section_role in {"step", "prerequisite"}:
                bonus += 0.04
                reasons.append("procedure_chunk_role")
        elif candidate_intent == "procedure" and candidate["type"] == "knowledge_unit":
            unit_type = str((candidate.get("knowledge_unit") or {}).unit_type if candidate.get("knowledge_unit") else "").lower()
            if unit_type in {"procedure_step", "condition", "exception"}:
                bonus += 0.08
                reasons.append("procedure_unit")
        elif candidate_intent == "procedure" and candidate["type"] == "section_summary" and any(role in {"step", "prerequisite", "exception"} for role in section_roles):
            bonus += 0.09
            reasons.append("procedure_section")
        elif candidate_intent == "procedure" and candidate["type"] == "notebook_note" and any(role in {"step", "exception"} for role in note_roles):
            bonus += 0.1
            reasons.append("procedure_notebook")
        elif candidate_intent == "procedure" and candidate["type"] == "artifact_summary" and artifact_type in {"table", "structure", "notebook"}:
            bonus += 0.07
            reasons.append("procedure_artifact")
        elif candidate_intent in {"policy_rule", "threshold", "conflict_check", "authority_check"} and candidate["type"] == "claim":
            bonus += 0.08
            reasons.append("policy_claim")
        elif candidate_intent in {"policy_rule", "threshold", "conflict_check", "authority_check"} and candidate["type"] == "knowledge_unit":
            unit_type = str((candidate.get("knowledge_unit") or {}).unit_type if candidate.get("knowledge_unit") else "").lower()
            if unit_type in {"rule", "condition", "threshold", "decision", "warning"}:
                bonus += 0.08
                reasons.append("policy_unit")
        elif candidate_intent in {"policy_rule", "threshold", "conflict_check", "authority_check"} and candidate["type"] == "section_summary" and any(role in {"rule", "scope", "exception"} for role in section_roles):
            bonus += 0.08
            reasons.append("policy_section")
        elif candidate_intent in {"policy_rule", "threshold", "conflict_check", "authority_check"} and candidate["type"] == "notebook_note" and any(role in {"evidence", "summary", "exception"} for role in note_roles):
            bonus += 0.09
            reasons.append("policy_notebook")
        elif candidate_intent in {"policy_rule", "threshold", "conflict_check", "authority_check"} and candidate["type"] == "artifact_summary" and artifact_type in {"table", "ocr", "structure", "notebook"}:
            bonus += 0.07
            reasons.append("policy_artifact")
        elif candidate_intent == "risk_review" and candidate["type"] == "section_summary" and any(role in {"exception", "warning", "risk"} for role in section_roles):
            bonus += 0.09
            reasons.append("risk_surface")
        elif candidate_intent == "risk_review" and candidate["type"] == "notebook_note" and any(role in {"exception", "summary"} for role in note_roles):
            bonus += 0.1
            reasons.append("risk_notebook")
        elif candidate_intent == "risk_review" and candidate["type"] == "artifact_summary" and any(tag in {"table", "ocr", "evidence"} for tag in artifact_tags):
            bonus += 0.06
            reasons.append("risk_artifact")
        elif candidate_intent == "summary" and candidate["type"] == "notebook_note" and any(role in {"summary", "definition", "evidence"} for role in note_roles):
            bonus += 0.1
            reasons.append("summary_notebook")
        elif candidate_intent == "summary" and candidate["type"] == "artifact_summary" and artifact_type in {"structure", "notebook", "ocr"}:
            bonus += 0.09
            reasons.append("summary_artifact")
        elif candidate_intent == "risk_review" and candidate["type"] == "chunk":
            if chunk_section_role in {"exception", "warning", "risk"} or any(marker in text_lower for marker in {"risk", "risks", "caveat", "warning"}):
                bonus += 0.09
                reasons.append("risk_chunk")
        if candidate["type"] == "page_summary" and candidate.get("page") and candidate["page"].status == "published":
            bonus += 0.03
            reasons.append("published_page")
        if candidate.get("planningStepIds"):
            bonus += min(0.06, len(candidate.get("planningStepIds") or []) * 0.02)
            reasons.append(f"multi_step_support:{len(candidate.get('planningStepIds') or [])}")
        rerank_score = round(candidate["score"] + bonus - (index * 0.002), 6)
        candidate["rerank_score"] = rerank_score
        candidate["diagnostics"]["rerankScore"] = rerank_score
        candidate["diagnostics"]["rerankReason"] = ", ".join(reasons) if reasons else "baseline_score"
        reranked.append(candidate)
    reranked.extend(candidates[limit:])
    reranked.sort(key=lambda item: item.get("rerank_score", item["score"]), reverse=True)
    return reranked


def _build_context_pack(candidates: list[dict], interpreted: dict, limit: int) -> tuple[list[dict], list[dict], dict]:
    return assemble_context_pack(
        candidates=candidates,
        interpreted=interpreted,
        limit=limit,
        retrieval_policy=_retrieval_policy,
        comparison_source_pairs=_comparison_source_pairs,
        conflict_builder=_build_conflicts,
    )


def _extract_first_number(text: str) -> float | None:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\b", text or "")
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _build_conflicts(candidates: list[dict], interpreted: dict) -> list[dict]:
    if interpreted["intent"] not in {"policy_rule", "threshold", "conflict_check", "authority_check", "correction_followup", "analysis"}:
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
            "summary": "Có nhiều nguồn liên quan với mức ưu tiên khác nhau; nên ưu tiên nguồn official hoặc approved hơn khi có xung đột.",
            "preferredSourceId": preferred["source"].id,
            "preferredSourceTitle": preferred["source"].title,
            "preferredReason": _source_authority_summary(preferred["source"], preferred.get("diagnostics")),
            "competingSourceId": competing["source"].id,
            "competingSourceTitle": competing["source"].title,
            "competingReason": _source_authority_summary(competing["source"], competing.get("diagnostics")),
        }
    ]


def _comparison_source_pairs(candidates: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    seen_sources: set[str] = set()
    for candidate in candidates:
        source = candidate.get("source")
        if not source:
            continue
        if source.id in seen_sources:
            continue
        seen_sources.add(source.id)
        pairs.append(candidate)
        if len(pairs) >= 2:
            break
    return pairs


def _format_answer_sections(
    question: str,
    selected: list[dict],
    interpreted: dict,
    conflicts: list[dict],
    language: str = "en",
    suggested_prompts: list[dict] | None = None,
    uncertainty: str | None = None,
) -> str:
    is_vi = language == "vi"
    if not selected:
        if is_vi:
            return (
                "## Trả lời trực tiếp\n\n"
                f"Tôi chưa có đủ bằng chứng grounded để trả lời **{question}** từ knowledge base hiện tại.\n\n"
                "## Lý do\n\n"
                "Không có source, page summary, notebook note, claim, hoặc chunk nào đủ hỗ trợ để chọn.\n\n"
                "## Độ bất định / Thiếu bằng chứng\n\n"
                "Bạn hãy nêu rõ source, page, section, hoặc term cụ thể để làm neo trả lời."
            )
        return (
            "## Direct Answer\n\n"
            f"I do not yet have enough grounded evidence to answer **{question}** from the current knowledge base.\n\n"
            "## Why\n\n"
            "No source, page summary, notebook note, claim, or chunk was selected with enough grounded support.\n\n"
            "## Uncertainty / Missing Evidence\n\n"
            "Try naming the exact source, page, section, or term that should anchor the answer."
        )
    top = selected[0]
    top_source = top.get("source")
    top_excerpt = top.get("excerpt", "").strip()
    direct = top["text"][:320].strip()
    why_line = (
        f"Câu trả lời này được dẫn dắt bởi **{top_source.title}** thông qua bằng chứng `{top['type']}`."
        if is_vi and top_source
        else f"Câu trả lời này được dẫn dắt bởi bằng chứng `{top['type']}` được chọn cho intent `{interpreted.get('intent')}`."
        if is_vi
        else f"This answer is driven first by **{top_source.title}** via `{top['type']}` evidence."
        if top_source
        else f"This answer is driven first by `{top['type']}` evidence selected for intent `{interpreted.get('intent')}`."
    )
    lines = ["## Trả lời trực tiếp" if is_vi else "## Direct Answer", "", direct, "", "## Lý do" if is_vi else "## Why", "", why_line]
    if top_excerpt:
        lines.extend(["", f"Tín hiệu grounded chính: {top_excerpt}" if is_vi else f"Primary grounded signal: {top_excerpt}"])
    lines.extend(["", "## Bằng chứng theo nguồn" if is_vi else "## Evidence By Source", ""])
    for candidate in selected[:3]:
        label = candidate["source"].title if candidate.get("source") else candidate["page"].title if candidate.get("page") else candidate["type"]
        reason = candidate.get("diagnostics", {}).get("rerankReason")
        reason_suffix = f" | rerank: {reason}" if reason else ""
        lines.append(f"- **{label}** (`{candidate['type']}`): {candidate['excerpt'].strip()}{reason_suffix}")
    if conflicts:
        lines.extend(["", "## Xung đột / Lưu ý" if is_vi else "## Conflicts / Caveats", ""])
        for conflict in conflicts:
            lines.append(
                f"- {conflict['summary']} Preferred: **{conflict.get('preferredSourceTitle') or 'N/A'}** "
                f"({conflict.get('preferredReason') or 'no authority note'}). "
                f"Competing: **{conflict.get('competingSourceTitle') or 'N/A'}** "
                f"({conflict.get('competingReason') or 'no authority note'})."
            )
    if uncertainty:
        lines.extend(["", "## Độ bất định / Thiếu bằng chứng" if is_vi else "## Uncertainty / Missing Evidence", "", uncertainty])
    if suggested_prompts:
        lines.extend(["", "## Gợi ý câu hỏi tiếp theo" if is_vi else "## Recommended Next Question", "", f"- {suggested_prompts[0]['text']}"])
    return "\n".join(lines).strip()


def _normalize_answer_language(answer: str, answer_language: str, source_languages: list[str], *, used_llm_answer: bool) -> str:
    if answer_language != "vi":
        return answer
    normalized = answer or ""
    heading_map = {
        "## Direct Answer": "## Tra loi truc tiep",
        "## Why": "## Ly do",
        "## Evidence By Source": "## Bang chung theo nguon",
        "## Conflicts / Caveats": "## Xung dot / Luu y",
        "## Uncertainty / Missing Evidence": "## Do bat dinh / Thieu bang chung",
        "## Recommended Next Question": "## Goi y cau hoi tiep theo",
    }
    heading_map = {
        "## Direct Answer": "## Trả lời trực tiếp",
        "## Why": "## Lý do",
        "## Evidence By Source": "## Bằng chứng theo nguồn",
        "## Conflicts / Caveats": "## Xung đột / Lưu ý",
        "## Uncertainty / Missing Evidence": "## Độ bất định / Thiếu bằng chứng",
        "## Recommended Next Question": "## Gợi ý câu hỏi tiếp theo",
    }
    for en_heading, vi_heading in heading_map.items():
        normalized = normalized.replace(en_heading, vi_heading)
    if _looks_english_heavy(normalized):
        source_hint = ", ".join(source_languages).upper() if source_languages else "N/A"
        prefix = (
            "Lưu ý: Câu trả lời dưới đây được tạo từ nguồn tài liệu gốc (có thể là tiếng Anh). "
            f"Ngôn ngữ nguồn: {source_hint}. "
            "Bạn có thể bật model trả lời để dịch đầy đủ thông tin sang tiếng Việt."
        )
        if used_llm_answer:
            prefix = (
                "Lưu ý: Hệ thống đã ưu tiên bằng chứng nguồn gốc. Nếu còn đoạn tiếng Anh, "
                "hãy tăng cường cấu hình model để dịch tiếng Việt chất lượng cao hơn."
            )
        normalized = f"{prefix}\n\n{normalized}"
    return normalized


def _build_clarification_response(session_id: str, question: str, interpreted: dict, runtime, scope: dict | None = None) -> dict:
    answer = interpreted.get("clarificationQuestion") or "Tôi cần thêm ngữ cảnh trước khi trả lời chính xác."
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"ask-{uuid4().hex[:8]}",
        "sessionId": session_id,
        "question": question,
        "answer": answer,
        "answerType": "clarification",
        "interpretedQuery": interpreted,
        "scope": scope,
        "suggestedPrompts": _dedupe_prompt_payloads(
            [
                ("Summarize this source first.", "clarify", "Start from a grounded summary before follow-up."),
                ("Which exact section or term do you want to correct?", "clarify", "Ask the user to point to the exact target."),
                ("What source or page should this question stay inside?", "scope", "Use scope to reduce ambiguity."),
            ],
            limit=4,
        ),
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
            "planning": interpreted.get("planner"),
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


def _build_candidate_citation(index: int, candidate: dict, query: str) -> dict | None:
    source = candidate.get("source")
    if not source:
        return None
    candidate_type = str(candidate.get("type") or "")
    score = float(candidate.get("score") or 0.0)
    if candidate_type == "chunk" and candidate.get("chunk") is not None:
        payload = _build_citation_payload(index, score, candidate["chunk"], source, query)
        payload["candidateType"] = "chunk"
        return payload
    if candidate_type == "claim" and candidate.get("chunk") is not None:
        payload = _build_citation_payload(index, score, candidate["chunk"], source, query)
        payload["candidateType"] = "claim"
        return payload
    if candidate_type == "knowledge_unit" and candidate.get("knowledge_unit") is not None:
        unit = candidate["knowledge_unit"]
        text = str(unit.text or "").strip()
        return {
            "id": f"cit-{index}",
            "index": index,
            "sourceId": source.id,
            "sourceTitle": source.title,
            "candidateType": "knowledge_unit",
            "chunkId": unit.source_chunk_id,
            "unitId": unit.id,
            "sectionKey": (unit.metadata_json or {}).get("parentSectionKey"),
            "sectionTitle": (unit.metadata_json or {}).get("parentSectionTitle") or unit.topic,
            "snippet": text[:280],
            "matchedText": text[:140] if text else None,
            "chunkSpanStart": unit.evidence_span_start,
            "chunkSpanEnd": unit.evidence_span_end,
            "sourceSpanStart": unit.evidence_span_start,
            "sourceSpanEnd": unit.evidence_span_end,
            "pageId": None,
            "pageTitle": None,
            "url": source.url,
            "confidence": round(min(score * 100, 99), 2),
        }
    if candidate_type == "notebook_note" and candidate.get("notebook_note") is not None:
        note = candidate["notebook_note"]
        if candidate.get("chunk") is not None:
            payload = _build_citation_payload(index, score, candidate["chunk"], source, query)
            payload["candidateType"] = "notebook_note"
            payload["sectionTitle"] = str(note.get("title") or "")
            return payload
        text = str(note.get("text") or "").strip()
        provenance = note.get("provenance") or {}
        section_keys = provenance.get("sectionKeys") or []
        return {
            "id": f"cit-{index}",
            "index": index,
            "sourceId": source.id,
            "sourceTitle": source.title,
            "candidateType": "notebook_note",
            "chunkId": None,
            "unitId": None,
            "sectionKey": str(section_keys[0]) if section_keys else None,
            "sectionTitle": str(note.get("title") or ""),
            "snippet": text[:280],
            "matchedText": text[:140] if text else None,
            "chunkSpanStart": None,
            "chunkSpanEnd": None,
            "sourceSpanStart": None,
            "sourceSpanEnd": None,
            "pageId": None,
            "pageTitle": None,
            "url": source.url,
            "confidence": round(min(score * 100, 99), 2),
        }
    if candidate_type == "user_note" and candidate.get("note") is not None:
        note = candidate["note"]
        anchor = candidate.get("note_anchor")
        text = str((anchor.snippet if anchor else "") or note.body or "").strip()
        return {
            "id": f"cit-{index}",
            "index": index,
            "sourceId": source.id,
            "sourceTitle": source.title,
            "candidateType": "user_note",
            "chunkId": anchor.chunk_id if anchor else None,
            "unitId": None,
            "sectionKey": anchor.section_key if anchor else None,
            "sectionTitle": note.title,
            "snippet": text[:280],
            "matchedText": text[:140] if text else None,
            "chunkSpanStart": None,
            "chunkSpanEnd": None,
            "sourceSpanStart": None,
            "sourceSpanEnd": None,
            "pageId": anchor.page_id if anchor else None,
            "pageTitle": None,
            "url": source.url,
            "confidence": round(min(score * 100, 99), 2),
        }
    if candidate_type == "section_summary" and candidate.get("section_summary") is not None:
        section = candidate["section_summary"]
        summary = str(section.get("summary") or "").strip()
        return {
            "id": f"cit-{index}",
            "index": index,
            "sourceId": source.id,
            "sourceTitle": source.title,
            "candidateType": "section_summary",
            "chunkId": None,
            "unitId": None,
            "sectionKey": section.get("sectionKey"),
            "sectionTitle": section.get("title"),
            "snippet": summary[:280],
            "matchedText": summary[:140] if summary else None,
            "chunkSpanStart": None,
            "chunkSpanEnd": None,
            "sourceSpanStart": None,
            "sourceSpanEnd": None,
            "pageId": None,
            "pageTitle": None,
            "url": source.url,
            "confidence": round(min(score * 100, 99), 2),
        }
    if candidate_type == "artifact_summary" and candidate.get("artifact") is not None:
        artifact = candidate["artifact"]
        text = _artifact_summary_text(artifact)
        return {
            "id": f"cit-{index}",
            "index": index,
            "sourceId": source.id,
            "sourceTitle": source.title,
            "candidateType": "artifact_summary",
            "artifactId": str(artifact.get("id") or ""),
            "artifactType": str(artifact.get("artifactType") or ""),
            "chunkId": None,
            "unitId": None,
            "sectionKey": None,
            "sectionTitle": str(artifact.get("title") or ""),
            "snippet": text[:280],
            "matchedText": text[:140] if text else None,
            "chunkSpanStart": None,
            "chunkSpanEnd": None,
            "sourceSpanStart": None,
            "sourceSpanEnd": None,
            "pageId": None,
            "pageTitle": None,
            "url": artifact.get("url") or source.url,
            "confidence": round(min(score * 100, 99), 2),
        }
    return None


def _decorate_citation_payload(payload: dict, candidate: dict, query: str) -> dict:
    payload["evidenceGrade"] = candidate_evidence_grade(query, candidate)
    payload["citationReason"] = citation_reason(query, candidate)
    return payload


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


def record_answer_feedback(
    db: Session,
    *,
    answer_id: str,
    message_id: str | None,
    rating: str,
    comment: str | None,
    actor=None,
) -> dict:
    allowed = {"helpful", "wrong", "missing_source", "bad_citation"}
    normalized = (rating or "").strip().lower()
    if normalized not in allowed:
        raise ValueError("rating must be one of: helpful, wrong, missing_source, bad_citation")
    object_id = (message_id or answer_id or "unknown")[:64]
    create_audit_log(
        db,
        action="ask_feedback",
        object_type="ask_answer",
        object_id=object_id,
        actor=getattr(actor, "name", None) or "Current User",
        summary=f"Ask feedback: {normalized}",
        metadata={
            "answerId": answer_id,
            "messageId": message_id,
            "rating": normalized,
            "comment": (comment or "").strip()[:1000],
            "actorUserId": getattr(actor, "id", None),
        },
    )
    db.commit()
    return {"success": True, "rating": normalized, "objectId": object_id}


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


def search(db: Session, query: str, result_type: str = "all", limit: int = 10, actor=None) -> list[dict]:
    runtime = load_runtime_snapshot(db)
    limit = max(1, min(limit, runtime.search_result_limit, 100))
    query_embedding = _embed_query(runtime, query)
    results: list[dict] = []
    terms = _query_terms(query)

    if result_type in {"all", "page"}:
        page_query = (
            _searchable_source_filter(
                db.query(Page)
                .join(PageSourceLink, PageSourceLink.page_id == Page.id)
                .join(Source, PageSourceLink.source_id == Source.id)
            )
        )
        page_query = page_query.filter(Page.status.in_(SEARCHABLE_PAGE_STATUSES))
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

    if actor is not None and result_type in {"all", "note"}:
        note_query = db.query(Note, NoteAnchor, Source).join(NoteAnchor, NoteAnchor.note_id == Note.id).join(Source, NoteAnchor.source_id == Source.id).filter(Note.status == "active")
        visibility_filters = [Note.scope == "workspace"]
        if getattr(actor, "id", None):
            visibility_filters.append(Note.owner_id == actor.id)
        if getattr(actor, "collection_scope_mode", "all") == "restricted":
            accessible = list(getattr(actor, "accessible_collection_ids", ()) or [])
            if accessible:
                visibility_filters.append(Note.collection_id.in_(accessible))
        else:
            visibility_filters.append(Note.scope == "collection")
        note_query = note_query.filter(or_(*visibility_filters))
        if terms:
            filters = []
            for term in terms[:6]:
                like = f"%{term}%"
                filters.extend([Note.title.ilike(like), Note.body.ilike(like), NoteAnchor.snippet.ilike(like), Source.title.ilike(like)])
            note_query = note_query.filter(or_(*filters))
        for note, anchor, source in note_query.limit(max(limit * 5, 50)).all():
            if not can_access_collection_id(actor, source.collection_id):
                continue
            text = f"{note.title}\n{note.body}\n{anchor.snippet}"
            diagnostics = _score_components(query, text, f"{source.title} {note.title}", runtime.hybrid_semantic_weight, query_embedding)
            score = diagnostics["finalScore"]
            if score > 0:
                results.append(
                    {
                        "id": note.id,
                        "type": "note",
                        "title": note.title,
                        "excerpt": (anchor.snippet or note.body)[:220],
                        "pageId": anchor.page_id,
                        "pageSlug": None,
                        "sourceId": source.id,
                        "relevanceScore": round(score * 100, 2),
                        "status": note.status,
                        "diagnostics": diagnostics,
                    }
                )

    results.sort(key=lambda item: item["relevanceScore"], reverse=True)
    return results[:limit]


def ask(
    db: Session,
    question: str,
    session_id: str | None = None,
    source_id: str | None = None,
    collection_id: str | None = None,
    page_id: str | None = None,
    actor=None,
) -> dict:
    answer_language = _detect_question_language(question)
    runtime = load_runtime_snapshot(db)
    ask_policy = dict(getattr(runtime, "ask_policy", {}) or {})
    query_variants = _build_query_variants(
        question,
        answer_language,
        cross_lingual_enabled=bool(ask_policy.get("crossLingualRewriteEnabled", True)),
    )
    session = _ensure_chat_session(db, session_id, question)
    recent_messages = _recent_session_messages(db, session.id)
    interpreted = _build_query_understanding(
        question,
        recent_messages,
        source_id=source_id,
        collection_id=collection_id,
        page_id=page_id,
    )
    interpreted["answerLanguage"] = answer_language
    interpreted["queryVariants"] = query_variants
    scope_summary = _resolve_scope_summary(
        db,
        source_id=interpreted.get("filters", {}).get("source_id"),
        collection_id=interpreted.get("filters", {}).get("collection_id"),
        page_id=interpreted.get("filters", {}).get("page_id"),
    )
    if interpreted["needsClarification"]:
        response = _build_clarification_response(session.id, question, interpreted, runtime, scope=scope_summary)
        now = datetime.now(timezone.utc)
        db.add(ChatMessage(id=f"msg-{uuid4().hex[:8]}", session_id=session.id, role="user", content=question, response_json=None, created_at=now))
        db.add(ChatMessage(id=response["id"], session_id=session.id, role="assistant", content=response["answer"], response_json=response, created_at=now))
        session.updated_at = now
        db.commit()
        return response

    standalone_query = interpreted["standaloneQuery"]
    primary_variant_query = str(query_variants[0]["query"] if query_variants else standalone_query)
    query_embedding = _embed_query(runtime, primary_variant_query)
    candidates = _retrieve_candidates(db, runtime, interpreted, query_embedding, query_variants=query_variants, actor=actor)
    candidates, blocked_candidate_count = _enforce_candidate_permissions(candidates, actor)
    reranked_candidates = _rerank_candidates(candidates, interpreted, limit=max(runtime.retrieval_limit * 3, 12))
    reranked_candidates, blocked_reranked_count = _enforce_candidate_permissions(reranked_candidates, actor)
    selected_candidates, context_pack, context_coverage = _build_context_pack(reranked_candidates, interpreted, runtime.retrieval_limit)
    selected_candidates, blocked_selected_count = _enforce_candidate_permissions(selected_candidates, actor)
    if scope_summary and selected_candidates and not _has_grounded_scope_match(selected_candidates):
        selected_candidates = []
        context_pack = []
        context_coverage = {"selectedCount": 0, "scopeExhausted": True}
    if selected_candidates and not _evidence_covers_question_terms(question, selected_candidates):
        selected_candidates = []
        context_pack = []
        context_coverage = {"selectedCount": 0, "termCoverageInsufficient": True}
    evidence_gate = evaluate_retrieval_quality(
        question=standalone_query,
        interpreted=interpreted,
        reranked_candidates=reranked_candidates,
        selected_candidates=selected_candidates,
        context_coverage=context_coverage,
        scope_summary=scope_summary,
    )
    min_top_score = float(ask_policy.get("minimumTopScore", 0.45))
    min_term_coverage = float(ask_policy.get("minimumTermCoverage", 0.35))
    if float(evidence_gate.get("topScore") or 0.0) < min_top_score:
        evidence_gate["passed"] = False
        evidence_gate["status"] = EVIDENCE_STATUS_INSUFFICIENT
        evidence_gate["reason"] = f"top_score_below_policy:{min_top_score:.2f}"
        evidence_gate.setdefault("warnings", []).append("Top retrieval score is below runtime ask policy threshold.")
    if float(evidence_gate.get("coverage") or 0.0) < min_term_coverage:
        evidence_gate["status"] = EVIDENCE_STATUS_PARTIAL if evidence_gate.get("passed") else EVIDENCE_STATUS_INSUFFICIENT
        evidence_gate["reason"] = f"coverage_below_policy:{min_term_coverage:.2f}"
        evidence_gate.setdefault("warnings", []).append("Query-term coverage is below runtime ask policy threshold.")
    source_languages = _infer_source_languages(selected_candidates)
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

    citation_pool = selected_candidates + [
        candidate
        for candidate in reranked_candidates[: max(runtime.retrieval_limit * 3, 12)]
        if (candidate["type"], candidate["id"]) not in {(item["type"], item["id"]) for item in selected_candidates}
    ]
    citation_candidates = select_citation_candidates(standalone_query, interpreted, citation_pool)
    citation_candidates, blocked_citation_count = _enforce_candidate_permissions(citation_candidates, actor)
    citations: list[dict] = []
    for index, candidate in enumerate(citation_candidates, start=1):
        payload = _build_candidate_citation(index, candidate, standalone_query)
        if payload is not None:
            citations.append(_decorate_citation_payload(payload, candidate, standalone_query))

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
    answer_mode = ANSWER_MODE_ANSWER
    evidence_status = EVIDENCE_STATUS_SUPPORTED
    if not evidence_gate.get("passed"):
        answer_mode = ANSWER_MODE_NO_ANSWER
        evidence_status = EVIDENCE_STATUS_INSUFFICIENT
    elif evidence_gate.get("status") == EVIDENCE_STATUS_PARTIAL:
        answer_mode = ANSWER_MODE_PARTIAL
        evidence_status = EVIDENCE_STATUS_PARTIAL
    if answer_mode == ANSWER_MODE_PARTIAL and not bool(ask_policy.get("allowPartialAnswers", True)):
        answer_mode = ANSWER_MODE_NO_ANSWER
        evidence_status = EVIDENCE_STATUS_INSUFFICIENT

    if selected_candidates:
        uncertainty = None
        if scope_summary:
            scope_summary["matchedInScope"] = True
    else:
        if scope_summary:
            scope_summary["matchedInScope"] = False
            uncertainty = f"No grounded evidence was selected within the current {scope_summary['type']} scope."
        else:
            uncertainty = "No grounded evidence was selected from the indexed knowledge base."
    suggested_prompts = _build_suggested_prompts(
        db,
        question,
        interpreted,
        scope_summary,
        selected_candidates,
        conflicts,
        uncertainty,
    )
    answer = _format_answer_sections(
        question,
        selected_candidates,
        interpreted,
        conflicts,
        language=answer_language,
        suggested_prompts=suggested_prompts,
        uncertainty=uncertainty,
    )
    used_llm_answer = False
    answer_profile = runtime.profile_for_task("ask_answer")
    allow_general_fallback = bool(ask_policy.get("allowGeneralFallback", False))
    if answer_mode != ANSWER_MODE_NO_ANSWER and selected_candidates:
        source_language_hint = ", ".join(source_languages) if source_languages else "unknown"
        system_prompt = (
            "You are a grounded internal knowledge-base assistant. "
            "Use only provided evidence. "
            f"Answer in language code `{answer_language}`. "
            f"{'Respond strictly in Vietnamese. Do not switch to English unless quoting source text. ' if answer_language == 'vi' else ''}"
            f"Answer mode: `{answer_mode}`. Evidence status: `{evidence_status}`. "
            f"Source language(s): `{source_language_hint}`. "
            "Return concise markdown with sections: Direct Answer, Why, Evidence By Source, Conflicts / Caveats when needed, Uncertainty / Missing Evidence when needed, and Recommended Next Question when useful. "
            "If answer mode is partial_answer, include a section named Unsupported Parts that clearly lists what cannot be answered from evidence. "
            "When source language differs from answer language, translate only supported evidence and keep citations tied to original source text. "
            "If sources disagree, explain which source should be preferred and why using authority, approval, effective date, or version signals from the provided evidence. "
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
            f"Answer language: {answer_language}\n"
            f"Answer mode: {answer_mode}\n"
            f"Evidence status: {evidence_status}\n"
            f"Source languages: {source_language_hint}\n\n"
            f"Planner: {interpreted.get('planner')}\n\n"
            "Context:\n\n" + "\n\n---\n\n".join(context_blocks)
        )
        llm_answer = llm_client.complete(answer_profile, system_prompt, user_prompt)
        if llm_answer:
            answer = llm_answer.strip()
            used_llm_answer = True
    if answer_mode == ANSWER_MODE_NO_ANSWER and allow_general_fallback:
        fallback_prompt = (
            "You are providing non-official fallback guidance. "
            f"Answer in language code `{answer_language}`. "
            "State clearly this is general knowledge, not from internal knowledge base, and keep it short."
        )
        fallback_answer = llm_client.complete(
            answer_profile,
            fallback_prompt,
            f"User question: {question}\nReturn a short helpful answer with a warning line.",
        )
        if fallback_answer:
            answer_mode = ANSWER_MODE_GENERAL_FALLBACK
            evidence_status = EVIDENCE_STATUS_UNSUPPORTED
            answer = fallback_answer.strip()
            uncertainty = "General fallback mode was used because grounded internal evidence was insufficient."
    if answer_mode == ANSWER_MODE_NO_ANSWER:
        answer = _no_answer_text(answer_language)
        citations = []
        related_pages = []
        related_sources = []
        conflicts = []
    elif answer_mode == ANSWER_MODE_PARTIAL:
        answer = f"{_partial_answer_prefix(answer_language)}\n\n{answer}"

    if related_images:
        answer = _append_related_illustrations(answer, related_images)

    answer_verification = verify_answer_support(standalone_query, answer, interpreted, selected_candidates, citations)
    verifier_decision = str(answer_verification.get("finalDecision") or "").strip().lower()
    verifier_risk = str(answer_verification.get("risk") or "").strip().lower()
    if verifier_decision == ANSWER_MODE_NO_ANSWER:
        answer_mode = ANSWER_MODE_NO_ANSWER
        evidence_status = EVIDENCE_STATUS_UNSUPPORTED
        answer = _no_answer_text(answer_language)
        citations = []
        related_pages = []
        related_sources = []
        conflicts = []
    elif verifier_decision == ANSWER_MODE_PARTIAL:
        answer_mode = ANSWER_MODE_PARTIAL
        evidence_status = EVIDENCE_STATUS_PARTIAL
    elif verifier_decision == ANSWER_MODE_ANSWER and answer_mode != ANSWER_MODE_NO_ANSWER:
        answer_mode = ANSWER_MODE_ANSWER
        evidence_status = EVIDENCE_STATUS_SUPPORTED
    if not answer_verification.get("supported") and selected_candidates:
        if answer_mode == ANSWER_MODE_ANSWER:
            answer_mode = ANSWER_MODE_PARTIAL
            evidence_status = EVIDENCE_STATUS_PARTIAL
        uncertainty = uncertainty or "The answer is based on low-confidence evidence verification; inspect citations before using it."
    if verifier_risk == "high":
        uncertainty = uncertainty or "High verification risk: claims may exceed available evidence."
    if answer_mode == ANSWER_MODE_PARTIAL and answer_language == "vi" and not answer.startswith("Toi chi tim thay"):
        answer = f"{_partial_answer_prefix(answer_language)}\n\n{answer}"
    answer = _normalize_answer_language(
        answer,
        answer_language,
        source_languages,
        used_llm_answer=used_llm_answer,
    )

    confidence = round(min((selected_candidates[0]["score"] * 100) if selected_candidates else 45, 95), 2)
    response = {
        "id": f"ask-{uuid4().hex[:8]}",
        "sessionId": session.id,
        "question": question,
        "answer": answer,
        "answerType": interpreted["answerType"],
        "interpretedQuery": interpreted,
        "scope": scope_summary,
        "suggestedPrompts": suggested_prompts,
        "citations": citations,
        "relatedPages": related_pages,
        "relatedSources": related_sources,
        "answerMode": answer_mode,
        "answerLanguage": answer_language,
        "sourceLanguages": source_languages,
        "evidenceStatus": evidence_status,
        "evidenceGate": {
            **evidence_gate,
            "citationCount": len(citations),
        },
        "confidence": confidence,
        "isInference": not used_llm_answer,
        "uncertainty": uncertainty,
        "conflicts": conflicts,
        "retrievalDebugId": f"dbg-{uuid4().hex[:8]}",
        "diagnostics": {
            "candidateCount": len(candidates),
            "blockedCandidateCount": blocked_candidate_count,
            "blockedRerankedCount": blocked_reranked_count,
            "blockedSelectedCount": blocked_selected_count,
            "blockedCitationCount": blocked_citation_count,
            "retrievalLimit": runtime.retrieval_limit,
            "searchResultLimit": runtime.search_result_limit,
            "clarificationTriggered": False,
            "planning": interpreted.get("planner"),
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
                    section_title=(
                        candidate["chunk"].section_title if candidate.get("chunk")
                        else str((candidate.get("notebook_note") or {}).get("title") or "")
                        or getattr(candidate.get("note"), "title", "")
                        or str((candidate.get("artifact") or {}).get("title") or "")
                    ) or None,
                )
                for candidate in _diagnostic_candidates(reranked_candidates, interpreted, runtime.retrieval_limit * 3)
            ],
            "selectedContext": context_pack,
            "contextCoverage": context_coverage,
            "answerVerification": answer_verification,
            "evidenceGate": {
                **evidence_gate,
                "citationCount": len(citations),
            },
            "answerGeneration": {
                "mode": "llm" if used_llm_answer else ("retrieval_fallback" if answer_mode != ANSWER_MODE_NO_ANSWER else "no_answer_policy"),
                "provider": answer_profile.provider if used_llm_answer else None,
                "model": answer_profile.model if used_llm_answer else None,
                "reason": (
                    "Answer was drafted by the configured ask_answer model using selected evidence."
                    if used_llm_answer
                    else "Answer was blocked by no-answer policy due to insufficient evidence."
                    if answer_mode == ANSWER_MODE_NO_ANSWER
                    else "Answer was generated from deterministic retrieval/evidence formatting because no model answer was used."
                ),
            },
            "queryVariants": query_variants,
            "askPolicy": ask_policy,
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
