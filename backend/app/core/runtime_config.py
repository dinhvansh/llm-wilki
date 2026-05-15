from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.db.database import SessionLocal
from app.models import RuntimeConfig
from app.core.secrets import decrypt_secret, decrypt_task_profiles, encrypt_secret, encrypt_task_profiles


AI_TASK_KEYS = (
    "ingest_summary",
    "claim_extraction",
    "entity_glossary_timeline",
    "bpm_generation",
    "ask_answer",
    "review_assist",
    "embeddings",
)
ASK_POLICY_KEY = "__ask_policy__"
DEFAULT_ASK_POLICY = {
    "minimumTopScore": 0.45,
    "minimumTermCoverage": 0.35,
    "allowPartialAnswers": True,
    "allowGeneralFallback": False,
    "crossLingualRewriteEnabled": True,
}


@dataclass
class LLMProfile:
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout_seconds: int

    def to_payload(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "apiKey": self.api_key,
            "baseUrl": self.base_url,
            "timeoutSeconds": self.timeout_seconds,
        }


def default_profile() -> LLMProfile:
    return LLMProfile(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )


def _clone_profile(profile: LLMProfile) -> LLMProfile:
    return LLMProfile(
        provider=profile.provider,
        model=profile.model,
        api_key=profile.api_key,
        base_url=profile.base_url,
        timeout_seconds=profile.timeout_seconds,
    )


def _profile_from_record(*, provider: str, model: str, api_key: str, base_url: str, timeout_seconds: int) -> LLMProfile:
    return LLMProfile(
        provider=provider or "none",
        model=model or "",
        api_key=decrypt_secret(api_key),
        base_url=base_url or "",
        timeout_seconds=timeout_seconds or settings.LLM_TIMEOUT_SECONDS,
    )


def build_default_task_profiles(
    answer_profile: LLMProfile | None = None,
    ingest_profile: LLMProfile | None = None,
    embedding_profile: LLMProfile | None = None,
) -> dict[str, LLMProfile]:
    answer_profile = _clone_profile(answer_profile or default_profile())
    ingest_profile = _clone_profile(ingest_profile or default_profile())
    embedding_profile = _clone_profile(
        embedding_profile
        or LLMProfile(provider="none", model="", api_key="", base_url="", timeout_seconds=90)
    )
    return {
        "ingest_summary": _clone_profile(ingest_profile),
        "claim_extraction": _clone_profile(ingest_profile),
        "entity_glossary_timeline": _clone_profile(ingest_profile),
        "bpm_generation": _clone_profile(ingest_profile),
        "ask_answer": _clone_profile(answer_profile),
        "review_assist": _clone_profile(answer_profile),
        "embeddings": _clone_profile(embedding_profile),
    }


def normalize_task_profiles(
    raw_profiles: dict | None,
    *,
    answer_profile: LLMProfile,
    ingest_profile: LLMProfile,
    embedding_profile: LLMProfile,
) -> dict[str, LLMProfile]:
    defaults = build_default_task_profiles(answer_profile, ingest_profile, embedding_profile)
    raw_profiles = raw_profiles or {}
    normalized: dict[str, LLMProfile] = {}
    for task in AI_TASK_KEYS:
        fallback = defaults[task]
        raw = raw_profiles.get(task, {}) if isinstance(raw_profiles, dict) else {}
        normalized[task] = LLMProfile(
            provider=str(raw.get("provider", fallback.provider) or "none").strip() or "none",
            model=str(raw.get("model", fallback.model) or "").strip(),
            api_key=decrypt_secret(raw.get("apiKey", raw.get("api_key", fallback.api_key))),
            base_url=str(raw.get("baseUrl", raw.get("base_url", fallback.base_url)) or "").strip(),
            timeout_seconds=int(raw.get("timeoutSeconds", raw.get("timeout_seconds", fallback.timeout_seconds)) or fallback.timeout_seconds),
        )
    return normalized


def serialize_task_profiles(profiles: dict[str, LLMProfile]) -> dict[str, dict]:
    return {task: profiles[task].to_payload() for task in AI_TASK_KEYS}


@dataclass
class RuntimeConfigSnapshot:
    ai_task_profiles: dict[str, LLMProfile]
    chunk_mode: str
    chunk_size_words: int
    chunk_overlap_words: int
    retrieval_limit: int
    hybrid_semantic_weight: float
    search_result_limit: int
    graph_node_limit: int
    lint_page_limit: int
    auto_review_threshold: float
    ask_policy: dict

    def profile_for_task(self, task_name: str) -> LLMProfile:
        if task_name in self.ai_task_profiles:
            return self.ai_task_profiles[task_name]
        if task_name == "answer":
            return self.ai_task_profiles["ask_answer"]
        if task_name == "ingest":
            return self.ai_task_profiles["ingest_summary"]
        if task_name == "embedding":
            return self.ai_task_profiles["embeddings"]
        return default_profile()

    @property
    def answer_llm(self) -> LLMProfile:
        return self.profile_for_task("ask_answer")

    @property
    def ingest_llm(self) -> LLMProfile:
        return self.profile_for_task("ingest_summary")

    @property
    def embedding_profile(self) -> LLMProfile:
        return self.profile_for_task("embeddings")


RUNTIME_CONFIG_ID = "runtime-settings"


def _default_snapshot() -> RuntimeConfigSnapshot:
    default_llm = default_profile()
    embedding = LLMProfile(provider="none", model="", api_key="", base_url="", timeout_seconds=90)
    return RuntimeConfigSnapshot(
        ai_task_profiles=build_default_task_profiles(default_llm, default_llm, embedding),
        chunk_mode="structured",
        chunk_size_words=180,
        chunk_overlap_words=30,
        retrieval_limit=4,
        hybrid_semantic_weight=0.35,
        search_result_limit=20,
        graph_node_limit=250,
        lint_page_limit=500,
        auto_review_threshold=0.76,
        ask_policy=dict(DEFAULT_ASK_POLICY),
    )


def ensure_runtime_config(db: Session) -> RuntimeConfig:
    record = db.query(RuntimeConfig).filter(RuntimeConfig.id == RUNTIME_CONFIG_ID).first()
    if record:
        return record

    snapshot = _default_snapshot()
    ask_profile = snapshot.profile_for_task("ask_answer")
    ingest_profile = snapshot.profile_for_task("ingest_summary")
    embedding_profile = snapshot.profile_for_task("embeddings")
    record = RuntimeConfig(
        id=RUNTIME_CONFIG_ID,
        answer_provider=ask_profile.provider,
        answer_model=ask_profile.model,
        answer_api_key=encrypt_secret(ask_profile.api_key),
        answer_base_url=ask_profile.base_url,
        answer_timeout_seconds=ask_profile.timeout_seconds,
        ingest_provider=ingest_profile.provider,
        ingest_model=ingest_profile.model,
        ingest_api_key=encrypt_secret(ingest_profile.api_key),
        ingest_base_url=ingest_profile.base_url,
        ingest_timeout_seconds=ingest_profile.timeout_seconds,
        embedding_provider=embedding_profile.provider,
        embedding_model=embedding_profile.model,
        embedding_api_key=encrypt_secret(embedding_profile.api_key),
        embedding_base_url=embedding_profile.base_url,
        ai_task_profiles=encrypt_task_profiles(serialize_task_profiles(snapshot.ai_task_profiles)),
        chunk_mode=snapshot.chunk_mode,
        chunk_size_words=snapshot.chunk_size_words,
        chunk_overlap_words=snapshot.chunk_overlap_words,
        retrieval_limit=snapshot.retrieval_limit,
        hybrid_semantic_weight=snapshot.hybrid_semantic_weight,
        search_result_limit=snapshot.search_result_limit,
        graph_node_limit=snapshot.graph_node_limit,
        lint_page_limit=snapshot.lint_page_limit,
        auto_review_threshold=snapshot.auto_review_threshold,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def runtime_snapshot_from_record(record: RuntimeConfig) -> RuntimeConfigSnapshot:
    raw_task_profiles = decrypt_task_profiles(getattr(record, "ai_task_profiles", {}) or {})
    ask_policy = dict(DEFAULT_ASK_POLICY)
    policy_from_record = raw_task_profiles.get(ASK_POLICY_KEY)
    if isinstance(policy_from_record, dict):
        ask_policy.update(
            {
                "minimumTopScore": float(policy_from_record.get("minimumTopScore", ask_policy["minimumTopScore"])),
                "minimumTermCoverage": float(policy_from_record.get("minimumTermCoverage", ask_policy["minimumTermCoverage"])),
                "allowPartialAnswers": bool(policy_from_record.get("allowPartialAnswers", ask_policy["allowPartialAnswers"])),
                "allowGeneralFallback": bool(policy_from_record.get("allowGeneralFallback", ask_policy["allowGeneralFallback"])),
                "crossLingualRewriteEnabled": bool(policy_from_record.get("crossLingualRewriteEnabled", ask_policy["crossLingualRewriteEnabled"])),
            }
        )
    answer_profile = _profile_from_record(
        provider=record.answer_provider,
        model=record.answer_model,
        api_key=record.answer_api_key,
        base_url=record.answer_base_url,
        timeout_seconds=record.answer_timeout_seconds,
    )
    ingest_profile = _profile_from_record(
        provider=record.ingest_provider,
        model=record.ingest_model,
        api_key=record.ingest_api_key,
        base_url=record.ingest_base_url,
        timeout_seconds=record.ingest_timeout_seconds,
    )
    embedding_profile = _profile_from_record(
        provider=record.embedding_provider,
        model=record.embedding_model,
        api_key=record.embedding_api_key,
        base_url=record.embedding_base_url,
        timeout_seconds=90,
    )
    task_profiles = normalize_task_profiles(
        raw_task_profiles,
        answer_profile=answer_profile,
        ingest_profile=ingest_profile,
        embedding_profile=embedding_profile,
    )
    return RuntimeConfigSnapshot(
        ai_task_profiles=task_profiles,
        chunk_mode=getattr(record, "chunk_mode", "structured") or "structured",
        chunk_size_words=record.chunk_size_words,
        chunk_overlap_words=record.chunk_overlap_words,
        retrieval_limit=record.retrieval_limit,
        hybrid_semantic_weight=record.hybrid_semantic_weight,
        search_result_limit=record.search_result_limit,
        graph_node_limit=record.graph_node_limit,
        lint_page_limit=record.lint_page_limit,
        auto_review_threshold=record.auto_review_threshold,
        ask_policy=ask_policy,
    )


def load_runtime_snapshot(db: Session | None = None) -> RuntimeConfigSnapshot:
    if db is not None:
        return runtime_snapshot_from_record(ensure_runtime_config(db))

    session = SessionLocal()
    try:
        return runtime_snapshot_from_record(ensure_runtime_config(session))
    except SQLAlchemyError:
        return _default_snapshot()
    finally:
        session.close()
