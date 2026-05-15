from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter

import httpx
from sqlalchemy.orm import Session

from app.core.embedding_client import embedding_client
from app.core.llm_client import llm_client
from app.core.runtime_config import (
    ASK_POLICY_KEY,
    DEFAULT_ASK_POLICY,
    AI_TASK_KEYS,
    LLMProfile,
    build_default_task_profiles,
    ensure_runtime_config,
    normalize_task_profiles,
    runtime_snapshot_from_record,
    serialize_task_profiles,
)
from app.core.secrets import decrypt_secret, decrypt_task_profiles, encrypt_secret, encrypt_task_profiles, is_encrypted_secret
from app.services.audit import create_audit_log


STATIC_MODEL_OPTIONS = {
    "anthropic": [
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-opus-4-1",
    ],
}


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _task_profiles_payload(record) -> dict[str, dict]:
    snapshot = runtime_snapshot_from_record(record)
    return serialize_task_profiles(snapshot.ai_task_profiles)


def _public_profile(profile: dict) -> dict:
    return {
        **profile,
        "apiKey": "",
        "hasApiKey": bool(profile.get("apiKey")),
    }


def _public_task_profiles(task_profiles: dict[str, dict]) -> dict[str, dict]:
    return {task: _public_profile(profile) for task, profile in task_profiles.items()}


def _incoming_api_key(value: object, existing_value: str, provider: str) -> str:
    if provider == "none":
        return ""
    candidate = str(value or "").strip()
    if not candidate or candidate == "***":
        return existing_value or ""
    return candidate


def _derive_task_profiles(payload: dict, record) -> dict[str, dict]:
    existing_task_profiles = _task_profiles_payload(record)
    answer_provider = payload.get("answerProvider", record.answer_provider)
    ingest_provider = payload.get("ingestProvider", record.ingest_provider)
    embedding_provider = payload.get("embeddingProvider", record.embedding_provider)
    answer_profile = LLMProfile(
        provider=answer_provider,
        model=str(payload.get("answerModel", record.answer_model) or "").strip(),
        api_key=_incoming_api_key(payload.get("answerApiKey"), decrypt_secret(record.answer_api_key), answer_provider),
        base_url=str(payload.get("answerBaseUrl", record.answer_base_url) or "").strip(),
        timeout_seconds=int(payload.get("answerTimeoutSeconds", record.answer_timeout_seconds) or record.answer_timeout_seconds),
    )
    ingest_profile = LLMProfile(
        provider=ingest_provider,
        model=str(payload.get("ingestModel", record.ingest_model) or "").strip(),
        api_key=_incoming_api_key(payload.get("ingestApiKey"), decrypt_secret(record.ingest_api_key), ingest_provider),
        base_url=str(payload.get("ingestBaseUrl", record.ingest_base_url) or "").strip(),
        timeout_seconds=int(payload.get("ingestTimeoutSeconds", record.ingest_timeout_seconds) or record.ingest_timeout_seconds),
    )
    embedding_profile = LLMProfile(
        provider=embedding_provider,
        model=str(payload.get("embeddingModel", record.embedding_model) or "").strip(),
        api_key=_incoming_api_key(payload.get("embeddingApiKey"), decrypt_secret(record.embedding_api_key), embedding_provider),
        base_url=str(payload.get("embeddingBaseUrl", record.embedding_base_url) or "").strip(),
        timeout_seconds=90,
    )
    provided_task_profiles = payload.get("aiTaskProfiles") or {}
    if isinstance(provided_task_profiles, dict):
        prepared_task_profiles = {}
        for task in AI_TASK_KEYS:
            raw_profile = dict(provided_task_profiles.get(task, {}) or {})
            existing_profile = existing_task_profiles.get(task, {})
            provider = str(raw_profile.get("provider", existing_profile.get("provider", "none")) or "none").strip() or "none"
            raw_profile["apiKey"] = _incoming_api_key(raw_profile.get("apiKey"), str(existing_profile.get("apiKey") or ""), provider)
            prepared_task_profiles[task] = raw_profile
        provided_task_profiles = prepared_task_profiles
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


def _task_profiles_have_plaintext_secrets(task_profiles: dict | None) -> bool:
    for profile in (task_profiles or {}).values():
        if isinstance(profile, dict):
            api_key = str(profile.get("apiKey") or "")
            if api_key and not is_encrypted_secret(api_key):
                return True
    return False


def _encrypt_runtime_record_secrets(record) -> bool:
    raw_task_profiles = getattr(record, "ai_task_profiles", {}) or {}
    needs_update = any(
        value and not is_encrypted_secret(value)
        for value in (record.answer_api_key, record.ingest_api_key, record.embedding_api_key)
    ) or _task_profiles_have_plaintext_secrets(raw_task_profiles)
    if not needs_update:
        return False

    snapshot = runtime_snapshot_from_record(record)
    task_profiles = serialize_task_profiles(snapshot.ai_task_profiles)
    legacy = _legacy_fields_from_task_profiles(task_profiles)
    record.answer_api_key = encrypt_secret(legacy["answer_api_key"])
    record.ingest_api_key = encrypt_secret(legacy["ingest_api_key"])
    record.embedding_api_key = encrypt_secret(legacy["embedding_api_key"])
    record.ai_task_profiles = encrypt_task_profiles(task_profiles)
    return True


def _settings_payload(record) -> dict:
    task_profiles = _task_profiles_payload(record)
    raw_decrypted = decrypt_task_profiles(getattr(record, "ai_task_profiles", {}) or {})
    ask_policy = dict(DEFAULT_ASK_POLICY)
    if isinstance(raw_decrypted.get(ASK_POLICY_KEY), dict):
        ask_policy.update(raw_decrypted[ASK_POLICY_KEY])
    return {
        "answerProvider": record.answer_provider,
        "answerModel": record.answer_model,
        "answerApiKey": "",
        "answerBaseUrl": record.answer_base_url,
        "answerTimeoutSeconds": record.answer_timeout_seconds,
        "ingestProvider": record.ingest_provider,
        "ingestModel": record.ingest_model,
        "ingestApiKey": "",
        "ingestBaseUrl": record.ingest_base_url,
        "ingestTimeoutSeconds": record.ingest_timeout_seconds,
        "embeddingProvider": record.embedding_provider,
        "embeddingModel": record.embedding_model,
        "embeddingApiKey": "",
        "embeddingBaseUrl": record.embedding_base_url,
        "aiTaskProfiles": _public_task_profiles(task_profiles),
        "chunkMode": getattr(record, "chunk_mode", "structured") or "structured",
        "chunkSizeWords": record.chunk_size_words,
        "chunkOverlapWords": record.chunk_overlap_words,
        "retrievalLimit": record.retrieval_limit,
        "hybridSemanticWeight": record.hybrid_semantic_weight,
        "searchResultLimit": record.search_result_limit,
        "graphNodeLimit": record.graph_node_limit,
        "lintPageLimit": record.lint_page_limit,
        "autoReviewThreshold": record.auto_review_threshold,
        "askPolicy": {
            "minimumTopScore": float(ask_policy.get("minimumTopScore", DEFAULT_ASK_POLICY["minimumTopScore"])),
            "minimumTermCoverage": float(ask_policy.get("minimumTermCoverage", DEFAULT_ASK_POLICY["minimumTermCoverage"])),
            "allowPartialAnswers": bool(ask_policy.get("allowPartialAnswers", DEFAULT_ASK_POLICY["allowPartialAnswers"])),
            "allowGeneralFallback": bool(ask_policy.get("allowGeneralFallback", DEFAULT_ASK_POLICY["allowGeneralFallback"])),
            "crossLingualRewriteEnabled": bool(ask_policy.get("crossLingualRewriteEnabled", DEFAULT_ASK_POLICY["crossLingualRewriteEnabled"])),
        },
        "updatedAt": _iso(record.updated_at),
    }


def serialize_runtime_settings(db: Session) -> dict:
    record = ensure_runtime_config(db)
    changed = False
    if not getattr(record, "ai_task_profiles", None):
        record.ai_task_profiles = serialize_task_profiles(
            build_default_task_profiles(
                LLMProfile(record.answer_provider, record.answer_model, decrypt_secret(record.answer_api_key), record.answer_base_url, record.answer_timeout_seconds),
                LLMProfile(record.ingest_provider, record.ingest_model, decrypt_secret(record.ingest_api_key), record.ingest_base_url, record.ingest_timeout_seconds),
                LLMProfile(record.embedding_provider, record.embedding_model, decrypt_secret(record.embedding_api_key), record.embedding_base_url, 90),
            )
        )
        changed = True
    if _encrypt_runtime_record_secrets(record):
        changed = True
    if changed:
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
                    "hasApiKey": bool(before_profile.get("hasApiKey") or before_profile.get("apiKey")),
                },
                "after": {
                    "provider": after_profile.get("provider"),
                    "model": after_profile.get("model"),
                    "baseUrl": after_profile.get("baseUrl"),
                    "timeoutSeconds": after_profile.get("timeoutSeconds"),
                    "hasApiKey": bool(after_profile.get("hasApiKey") or after_profile.get("apiKey")),
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
            "askPolicy",
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
    record.answer_api_key = encrypt_secret(legacy["answer_api_key"])
    record.answer_base_url = legacy["answer_base_url"]
    record.answer_timeout_seconds = legacy["answer_timeout_seconds"]
    record.ingest_provider = legacy["ingest_provider"]
    record.ingest_model = legacy["ingest_model"]
    record.ingest_api_key = encrypt_secret(legacy["ingest_api_key"])
    record.ingest_base_url = legacy["ingest_base_url"]
    record.ingest_timeout_seconds = legacy["ingest_timeout_seconds"]
    record.embedding_provider = legacy["embedding_provider"]
    record.embedding_model = legacy["embedding_model"]
    record.embedding_api_key = encrypt_secret(legacy["embedding_api_key"])
    record.embedding_base_url = legacy["embedding_base_url"]
    record.chunk_mode = payload["chunkMode"]
    record.chunk_size_words = payload["chunkSizeWords"]
    record.chunk_overlap_words = payload["chunkOverlapWords"]
    record.retrieval_limit = payload["retrievalLimit"]
    record.hybrid_semantic_weight = payload["hybridSemanticWeight"]
    record.search_result_limit = payload["searchResultLimit"]
    record.graph_node_limit = payload["graphNodeLimit"]
    record.lint_page_limit = payload["lintPageLimit"]
    record.auto_review_threshold = payload["autoReviewThreshold"]
    ask_policy_payload = payload.get("askPolicy") or {}
    encrypted_raw_profiles = encrypt_task_profiles(task_profiles)
    encrypted_raw_profiles[ASK_POLICY_KEY] = {
        "minimumTopScore": float(ask_policy_payload.get("minimumTopScore", DEFAULT_ASK_POLICY["minimumTopScore"])),
        "minimumTermCoverage": float(ask_policy_payload.get("minimumTermCoverage", DEFAULT_ASK_POLICY["minimumTermCoverage"])),
        "allowPartialAnswers": bool(ask_policy_payload.get("allowPartialAnswers", DEFAULT_ASK_POLICY["allowPartialAnswers"])),
        "allowGeneralFallback": bool(ask_policy_payload.get("allowGeneralFallback", DEFAULT_ASK_POLICY["allowGeneralFallback"])),
        "crossLingualRewriteEnabled": bool(
            ask_policy_payload.get("crossLingualRewriteEnabled", DEFAULT_ASK_POLICY["crossLingualRewriteEnabled"])
        ),
    }
    record.ai_task_profiles = encrypted_raw_profiles
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


def list_runtime_models(payload: dict) -> dict:
    provider = str(payload.get("provider") or "none").strip()
    api_key = str(payload.get("apiKey") or "").strip()
    base_url = str(payload.get("baseUrl") or "").strip()
    timeout_seconds = int(payload.get("timeoutSeconds") or 90)
    started = perf_counter()
    models: list[str] = []

    try:
        if provider == "openai":
            if not api_key:
                raise ValueError("API key is required to load OpenAI models.")
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"})
                response.raise_for_status()
                payload_json = response.json()
            models = sorted(str(item.get("id")) for item in payload_json.get("data", []) if isinstance(item, dict) and item.get("id"))

        elif provider == "gemini":
            if not api_key:
                raise ValueError("API key is required to load Gemini models.")
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": api_key})
                response.raise_for_status()
                payload_json = response.json()
            for item in payload_json.get("models", []):
                if not isinstance(item, dict):
                    continue
                methods = item.get("supportedGenerationMethods") or []
                name = str(item.get("name") or "").removeprefix("models/")
                if name and "generateContent" in methods:
                    models.append(name)
            models = sorted(set(models))

        elif provider == "openai_compatible":
            if not base_url:
                raise ValueError("Base URL is required for OpenAI-compatible providers.")
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.get(f"{base_url.rstrip('/')}/models", headers=headers)
                response.raise_for_status()
                payload_json = response.json()
            models = sorted(str(item.get("id")) for item in payload_json.get("data", []) if isinstance(item, dict) and item.get("id"))

        elif provider == "ollama":
            target = (base_url or "http://host.docker.internal:11434").rstrip("/")
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.get(f"{target}/api/tags")
                response.raise_for_status()
                payload_json = response.json()
            models = sorted(str(item.get("name")) for item in payload_json.get("models", []) if isinstance(item, dict) and item.get("name"))

        elif provider in STATIC_MODEL_OPTIONS:
            models = STATIC_MODEL_OPTIONS[provider]

        else:
            raise ValueError("Choose OpenAI, Gemini, Anthropic, Ollama, or OpenAI-compatible before loading models.")

    except Exception as exc:
        return {
            "success": False,
            "provider": provider,
            "models": [],
            "message": str(exc) or "Could not load models.",
            "latencyMs": int((perf_counter() - started) * 1000),
        }

    return {
        "success": True,
        "provider": provider,
        "models": models,
        "message": f"Loaded {len(models)} model{'' if len(models) == 1 else 's'}.",
        "latencyMs": int((perf_counter() - started) * 1000),
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
    merged["askPolicy"] = {**(current.get("askPolicy") or {}), **(incoming.get("askPolicy") or {})}
    for key, value in list(merged.items()):
        if key.lower().endswith("apikey") and value == "***":
            merged[key] = current.get(key, "")
    return merged
