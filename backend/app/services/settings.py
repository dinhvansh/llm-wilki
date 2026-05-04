from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.embedding_client import embedding_client
from app.core.llm_client import llm_client
from app.core.runtime_config import (
    AI_TASK_KEYS,
    LLMProfile,
    build_default_task_profiles,
    ensure_runtime_config,
    normalize_task_profiles,
    runtime_snapshot_from_record,
    serialize_task_profiles,
)
from app.services.audit import create_audit_log


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _task_profiles_payload(record) -> dict[str, dict]:
    snapshot = runtime_snapshot_from_record(record)
    return serialize_task_profiles(snapshot.ai_task_profiles)


def _derive_task_profiles(payload: dict, record) -> dict[str, dict]:
    answer_profile = LLMProfile(
        provider=payload.get("answerProvider", record.answer_provider),
        model=str(payload.get("answerModel", record.answer_model) or "").strip(),
        api_key=str(payload.get("answerApiKey", record.answer_api_key) or "").strip(),
        base_url=str(payload.get("answerBaseUrl", record.answer_base_url) or "").strip(),
        timeout_seconds=int(payload.get("answerTimeoutSeconds", record.answer_timeout_seconds) or record.answer_timeout_seconds),
    )
    ingest_profile = LLMProfile(
        provider=payload.get("ingestProvider", record.ingest_provider),
        model=str(payload.get("ingestModel", record.ingest_model) or "").strip(),
        api_key=str(payload.get("ingestApiKey", record.ingest_api_key) or "").strip(),
        base_url=str(payload.get("ingestBaseUrl", record.ingest_base_url) or "").strip(),
        timeout_seconds=int(payload.get("ingestTimeoutSeconds", record.ingest_timeout_seconds) or record.ingest_timeout_seconds),
    )
    embedding_profile = LLMProfile(
        provider=payload.get("embeddingProvider", record.embedding_provider),
        model=str(payload.get("embeddingModel", record.embedding_model) or "").strip(),
        api_key=str(payload.get("embeddingApiKey", record.embedding_api_key) or "").strip(),
        base_url=str(payload.get("embeddingBaseUrl", record.embedding_base_url) or "").strip(),
        timeout_seconds=90,
    )
    provided_task_profiles = payload.get("aiTaskProfiles") or {}
    normalized = normalize_task_profiles(
        provided_task_profiles,
        answer_profile=answer_profile,
        ingest_profile=ingest_profile,
        embedding_profile=embedding_profile,
    )
    return serialize_task_profiles(normalized)


def _legacy_fields_from_task_profiles(task_profiles: dict[str, dict]) -> dict:
    ask = task_profiles["ask_answer"]
    ingest_summary = task_profiles["ingest_summary"]
    embeddings = task_profiles["embeddings"]
    return {
        "answer_provider": ask["provider"],
        "answer_model": ask["model"],
        "answer_api_key": ask["apiKey"],
        "answer_base_url": ask["baseUrl"],
        "answer_timeout_seconds": ask["timeoutSeconds"],
        "ingest_provider": ingest_summary["provider"],
        "ingest_model": ingest_summary["model"],
        "ingest_api_key": ingest_summary["apiKey"],
        "ingest_base_url": ingest_summary["baseUrl"],
        "ingest_timeout_seconds": ingest_summary["timeoutSeconds"],
        "embedding_provider": embeddings["provider"],
        "embedding_model": embeddings["model"],
        "embedding_api_key": embeddings["apiKey"],
        "embedding_base_url": embeddings["baseUrl"],
    }


def _settings_payload(record) -> dict:
    task_profiles = _task_profiles_payload(record)
    return {
        "answerProvider": record.answer_provider,
        "answerModel": record.answer_model,
        "answerApiKey": record.answer_api_key,
        "answerBaseUrl": record.answer_base_url,
        "answerTimeoutSeconds": record.answer_timeout_seconds,
        "ingestProvider": record.ingest_provider,
        "ingestModel": record.ingest_model,
        "ingestApiKey": record.ingest_api_key,
        "ingestBaseUrl": record.ingest_base_url,
        "ingestTimeoutSeconds": record.ingest_timeout_seconds,
        "embeddingProvider": record.embedding_provider,
        "embeddingModel": record.embedding_model,
        "embeddingApiKey": record.embedding_api_key,
        "embeddingBaseUrl": record.embedding_base_url,
        "aiTaskProfiles": task_profiles,
        "chunkMode": getattr(record, "chunk_mode", "structured") or "structured",
        "chunkSizeWords": record.chunk_size_words,
        "chunkOverlapWords": record.chunk_overlap_words,
        "retrievalLimit": record.retrieval_limit,
        "hybridSemanticWeight": record.hybrid_semantic_weight,
        "searchResultLimit": record.search_result_limit,
        "graphNodeLimit": record.graph_node_limit,
        "lintPageLimit": record.lint_page_limit,
        "autoReviewThreshold": record.auto_review_threshold,
        "updatedAt": _iso(record.updated_at),
    }


def serialize_runtime_settings(db: Session) -> dict:
    record = ensure_runtime_config(db)
    if not getattr(record, "ai_task_profiles", None):
        record.ai_task_profiles = serialize_task_profiles(
            build_default_task_profiles(
                LLMProfile(record.answer_provider, record.answer_model, record.answer_api_key, record.answer_base_url, record.answer_timeout_seconds),
                LLMProfile(record.ingest_provider, record.ingest_model, record.ingest_api_key, record.ingest_base_url, record.ingest_timeout_seconds),
                LLMProfile(record.embedding_provider, record.embedding_model, record.embedding_api_key, record.embedding_base_url, 90),
            )
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return _settings_payload(record)


def _extract_change_summary(before: dict, after: dict) -> dict:
    changed_tasks: dict[str, dict] = {}
    before_tasks = before.get("aiTaskProfiles", {})
    after_tasks = after.get("aiTaskProfiles", {})
    for task in AI_TASK_KEYS:
        before_profile = before_tasks.get(task, {})
        after_profile = after_tasks.get(task, {})
        if before_profile != after_profile:
            changed_tasks[task] = {
                "before": {
                    "provider": before_profile.get("provider"),
                    "model": before_profile.get("model"),
                    "baseUrl": before_profile.get("baseUrl"),
                    "timeoutSeconds": before_profile.get("timeoutSeconds"),
                    "hasApiKey": bool(before_profile.get("apiKey")),
                },
                "after": {
                    "provider": after_profile.get("provider"),
                    "model": after_profile.get("model"),
                    "baseUrl": after_profile.get("baseUrl"),
                    "timeoutSeconds": after_profile.get("timeoutSeconds"),
                    "hasApiKey": bool(after_profile.get("apiKey")),
                },
            }
    changed_scalar = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in (
            "chunkMode",
            "chunkSizeWords",
            "chunkOverlapWords",
            "retrievalLimit",
            "hybridSemanticWeight",
            "searchResultLimit",
            "graphNodeLimit",
            "lintPageLimit",
            "autoReviewThreshold",
        )
        if before.get(key) != after.get(key)
    }
    return {"changedTasks": changed_tasks, "changedScalars": changed_scalar}


def update_runtime_settings(db: Session, payload: dict, *, actor_name: str | None = None) -> dict:
    record = ensure_runtime_config(db)
    before = serialize_runtime_settings(db)
    task_profiles = _derive_task_profiles(payload, record)
    legacy = _legacy_fields_from_task_profiles(task_profiles)

    record.answer_provider = legacy["answer_provider"]
    record.answer_model = legacy["answer_model"]
    record.answer_api_key = legacy["answer_api_key"]
    record.answer_base_url = legacy["answer_base_url"]
    record.answer_timeout_seconds = legacy["answer_timeout_seconds"]
    record.ingest_provider = legacy["ingest_provider"]
    record.ingest_model = legacy["ingest_model"]
    record.ingest_api_key = legacy["ingest_api_key"]
    record.ingest_base_url = legacy["ingest_base_url"]
    record.ingest_timeout_seconds = legacy["ingest_timeout_seconds"]
    record.embedding_provider = legacy["embedding_provider"]
    record.embedding_model = legacy["embedding_model"]
    record.embedding_api_key = legacy["embedding_api_key"]
    record.embedding_base_url = legacy["embedding_base_url"]
    record.ai_task_profiles = task_profiles
    record.chunk_mode = payload["chunkMode"]
    record.chunk_size_words = payload["chunkSizeWords"]
    record.chunk_overlap_words = payload["chunkOverlapWords"]
    record.retrieval_limit = payload["retrievalLimit"]
    record.hybrid_semantic_weight = payload["hybridSemanticWeight"]
    record.search_result_limit = payload["searchResultLimit"]
    record.graph_node_limit = payload["graphNodeLimit"]
    record.lint_page_limit = payload["lintPageLimit"]
    record.auto_review_threshold = payload["autoReviewThreshold"]
    record.updated_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    after = serialize_runtime_settings(db)
    if actor_name:
        summary = _extract_change_summary(before, after)
        changed_tasks = list(summary["changedTasks"].keys())
        changed_scalars = list(summary["changedScalars"].keys())
        create_audit_log(
            db,
            action="runtime_settings_updated",
            object_type="runtime_config",
            object_id=record.id,
            actor=actor_name,
            summary="Updated task-scoped AI settings" if changed_tasks else "Updated runtime settings",
            metadata={
                "changedTasks": changed_tasks,
                "changedScalars": changed_scalars,
                "changes": summary,
            },
        )
        db.commit()
    return after


def test_runtime_connection(payload: dict) -> dict:
    profile = LLMProfile(
        provider=payload["provider"],
        model=payload["model"].strip(),
        api_key=payload["apiKey"].strip(),
        base_url=payload["baseUrl"].strip(),
        timeout_seconds=payload["timeoutSeconds"],
    )
    if not llm_client.is_enabled(profile):
        return {
            "success": False,
            "provider": profile.provider,
            "model": profile.model,
            "purpose": payload["purpose"],
            "message": "Choose a provider other than 'none' and set a model before testing.",
            "latencyMs": None,
        }

    started = perf_counter()
    if payload["purpose"] in {"embedding", "embeddings"}:
        vectors = embedding_client.embed_texts(profile, ["Embedding connection test."])
        response = "OK" if vectors and vectors[0] else None
    else:
        response = llm_client.complete(
            profile,
            "Reply with a single short line: OK",
            "Connection test. Reply exactly with OK.",
        )
    latency_ms = int((perf_counter() - started) * 1000)
    if response:
        return {
            "success": True,
            "provider": profile.provider,
            "model": profile.model,
            "purpose": payload["purpose"],
            "message": f"Connection succeeded. Model replied: {response[:80].strip()}",
            "latencyMs": latency_ms,
        }

    return {
        "success": False,
        "provider": profile.provider,
        "model": profile.model,
        "purpose": payload["purpose"],
        "message": "Connection failed. Check base URL, API key, model name, and provider availability.",
        "latencyMs": latency_ms,
    }


def redact_runtime_settings_payload(payload: dict) -> dict:
    redacted = deepcopy(payload)
    for key, value in list(redacted.items()):
        if key.lower().endswith("apikey") and value:
            redacted[key] = "***"
    task_profiles = redacted.get("aiTaskProfiles", {})
    for task, profile in task_profiles.items():
        if isinstance(profile, dict) and profile.get("apiKey"):
            task_profiles[task] = {**profile, "apiKey": "***"}
    redacted["aiTaskProfiles"] = task_profiles
    return redacted


def merge_runtime_settings_import(current: dict, incoming: dict) -> dict:
    merged = {**current, **incoming}
    current_tasks = current.get("aiTaskProfiles", {})
    incoming_tasks = incoming.get("aiTaskProfiles", {}) if isinstance(incoming.get("aiTaskProfiles", {}), dict) else {}
    merged_tasks = {}
    for task in AI_TASK_KEYS:
        current_profile = current_tasks.get(task, {})
        incoming_profile = incoming_tasks.get(task, {})
        merged_profile = {**current_profile, **incoming_profile}
        if merged_profile.get("apiKey") == "***":
            merged_profile["apiKey"] = current_profile.get("apiKey", "")
        merged_tasks[task] = merged_profile
    merged["aiTaskProfiles"] = merged_tasks
    for key, value in list(merged.items()):
        if key.lower().endswith("apikey") and value == "***":
            merged[key] = current.get(key, "")
    return merged
