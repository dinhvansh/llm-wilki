from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.llm_client import llm_client
from app.core.runtime_config import AI_TASK_KEYS, ensure_runtime_config, runtime_snapshot_from_record


ROOT = Path(__file__).resolve().parents[2]
SKILL_PACKAGE_DIR = ROOT / "skill_packages"
DEFAULT_TASK_PROFILE = "ask_answer"


def _package_paths() -> list[Path]:
    if not SKILL_PACKAGE_DIR.exists():
        return []
    return sorted(path for path in SKILL_PACKAGE_DIR.glob("*.json") if path.is_file())


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def _ensure_dir() -> None:
    SKILL_PACKAGE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_string_list(value) -> list[str]:
    if isinstance(value, str):
      return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list):
      return []
    return [str(item).strip() for item in value if str(item).strip()]


def _load_manifest(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    package_id = str(payload.get("id") or path.stem).strip()
    if not package_id:
        return None
    metadata = payload.get("metadataJson") if isinstance(payload.get("metadataJson"), dict) else {}
    test_history = metadata.get("testHistory") if isinstance(metadata.get("testHistory"), list) else []
    latest_test = test_history[-1] if test_history else None
    task_profile = str(metadata.get("taskProfile") or DEFAULT_TASK_PROFILE).strip() or DEFAULT_TASK_PROFILE
    if task_profile not in AI_TASK_KEYS:
        task_profile = DEFAULT_TASK_PROFILE
    return {
        "id": package_id,
        "name": str(payload.get("name") or package_id).strip(),
        "version": str(payload.get("version") or "0.1.0").strip(),
        "scope": str(payload.get("scope") or "workspace").strip(),
        "status": str(payload.get("status") or "draft").strip(),
        "summary": str(payload.get("summary") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "instructions": str(payload.get("instructions") or metadata.get("instructions") or "").strip(),
        "capabilities": _normalize_string_list(payload.get("capabilities") or []),
        "tags": _normalize_string_list(payload.get("tags") or []),
        "entryPoints": _normalize_string_list(payload.get("entryPoints") or []),
        "owner": str(payload.get("owner") or "").strip() or None,
        "reviewStatus": str(payload.get("reviewStatus") or "draft").strip(),
        "reviewHistory": payload.get("reviewHistory") if isinstance(payload.get("reviewHistory"), list) else [],
        "metadataJson": metadata,
        "taskProfile": task_profile,
        "latestTest": latest_test if isinstance(latest_test, dict) else None,
    }


def _find_package_path(package_id: str) -> Path | None:
    for path in _package_paths():
        manifest = _load_manifest(path)
        if manifest and manifest["id"] == package_id:
            return path
    return None


def _read_raw_manifest(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Skill manifest must be a JSON object")
    return payload


def _write_manifest(path: Path, payload: dict) -> dict:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    manifest = _load_manifest(path)
    if manifest is None:
        raise ValueError("Failed to reload skill manifest")
    return manifest


def _append_review_event(payload: dict, *, event_type: str, actor: str, comment: str | None = None) -> None:
    history = payload.get("reviewHistory")
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "id": f"skill-review-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "type": event_type,
            "actor": actor,
            "comment": (comment or "").strip() or None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    payload["reviewHistory"] = history


def _set_manifest_fields(payload: dict, update: dict, *, actor: str | None = None, is_create: bool = False) -> None:
    payload["id"] = update["id"]
    payload["name"] = update["name"]
    payload["version"] = update.get("version", payload.get("version") or "0.1.0")
    payload["scope"] = update.get("scope", payload.get("scope") or "workspace")
    payload["status"] = update.get("status", payload.get("status") or "draft")
    payload["summary"] = update.get("summary", "")
    payload["description"] = update.get("description", "")
    payload["instructions"] = update.get("instructions", "")
    payload["capabilities"] = _normalize_string_list(update.get("capabilities"))
    payload["tags"] = _normalize_string_list(update.get("tags"))
    payload["entryPoints"] = _normalize_string_list(update.get("entryPoints"))
    payload["owner"] = update.get("owner") or payload.get("owner") or actor or "Current User"
    payload["reviewStatus"] = update.get("reviewStatus", payload.get("reviewStatus") or "draft")
    metadata = payload.get("metadataJson") if isinstance(payload.get("metadataJson"), dict) else {}
    metadata.update(update.get("metadataJson") or {})
    metadata["taskProfile"] = update.get("taskProfile", metadata.get("taskProfile") or DEFAULT_TASK_PROFILE)
    payload["metadataJson"] = metadata
    if is_create and not isinstance(payload.get("reviewHistory"), list):
        payload["reviewHistory"] = []


def _build_system_prompt(manifest: dict) -> str:
    instructions = str(manifest.get("instructions") or "").strip()
    if instructions:
        return instructions
    capabilities = manifest.get("capabilities") or []
    entry_points = manifest.get("entryPoints") or []
    summary = str(manifest.get("summary") or "").strip()
    description = str(manifest.get("description") or "").strip()
    lines = [
        f"You are executing the skill package '{manifest.get('name')}'.",
        summary or "Respond according to the skill definition.",
    ]
    if description:
        lines.append(description)
    if capabilities:
        lines.append("Capabilities:")
        lines.extend(f"- {item}" for item in capabilities)
    if entry_points:
        lines.append("Typical entry points:")
        lines.extend(f"- {item}" for item in entry_points)
    lines.append("Return a direct, useful answer grounded in the skill intent.")
    return "\n".join(lines)


def list_skill_packages() -> list[dict]:
    packages: list[dict] = []
    for path in _package_paths():
        manifest = _load_manifest(path)
        if manifest is not None:
            packages.append(manifest)
    return packages


def get_skill_package(package_id: str) -> dict | None:
    path = _find_package_path(package_id)
    return _load_manifest(path) if path else None


def create_skill_package(payload: dict, *, actor: str) -> dict:
    _ensure_dir()
    package_id = _slugify(str(payload.get("id") or payload.get("name") or "").strip())
    if not package_id:
        raise ValueError("Skill id or name is required")
    if _find_package_path(package_id) is not None:
        raise ValueError("Skill package already exists")
    path = SKILL_PACKAGE_DIR / f"{package_id}.json"
    manifest: dict = {}
    _set_manifest_fields(
        manifest,
        {
            **payload,
            "id": package_id,
            "status": payload.get("status") or "draft",
            "reviewStatus": payload.get("reviewStatus") or "draft",
            "version": payload.get("version") or "0.1.0",
        },
        actor=actor,
        is_create=True,
    )
    _append_review_event(manifest, event_type="create", actor=actor, comment="Skill package created")
    return _write_manifest(path, manifest)


def update_skill_package(package_id: str, payload: dict, *, actor: str) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    manifest = _read_raw_manifest(path)
    _set_manifest_fields(
        manifest,
        {
          **payload,
          "id": package_id,
          "version": payload.get("version") or manifest.get("version") or "0.1.0",
          "status": payload.get("status") or manifest.get("status") or "draft",
          "reviewStatus": payload.get("reviewStatus") or manifest.get("reviewStatus") or "draft",
        },
        actor=actor,
    )
    _append_review_event(manifest, event_type="update", actor=actor, comment=payload.get("changeComment") or "Updated skill package")
    return _write_manifest(path, manifest)


def add_skill_review_comment(package_id: str, *, actor: str, comment: str) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    payload = _read_raw_manifest(path)
    _append_review_event(payload, event_type="comment", actor=actor, comment=comment)
    return _write_manifest(path, payload)


def submit_skill_for_review(package_id: str, *, actor: str, comment: str | None = None) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    payload = _read_raw_manifest(path)
    payload["reviewStatus"] = "in_review"
    payload["status"] = "draft"
    _append_review_event(payload, event_type="submit_review", actor=actor, comment=comment)
    return _write_manifest(path, payload)


def approve_skill_package(package_id: str, *, actor: str, comment: str | None = None) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    payload = _read_raw_manifest(path)
    payload["reviewStatus"] = "approved"
    payload["status"] = "ready"
    _append_review_event(payload, event_type="approve", actor=actor, comment=comment)
    return _write_manifest(path, payload)


def release_skill_package(package_id: str, *, actor: str, comment: str | None = None) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    payload = _read_raw_manifest(path)
    payload["reviewStatus"] = "released"
    payload["status"] = "released"
    _append_review_event(payload, event_type="release", actor=actor, comment=comment)
    return _write_manifest(path, payload)


def test_skill_package(package_id: str, *, actor: str, test_input: str, db: Session) -> dict | None:
    path = _find_package_path(package_id)
    if path is None:
        return None
    manifest = _read_raw_manifest(path)
    normalized = _load_manifest(path) or {}
    metadata = manifest.get("metadataJson") if isinstance(manifest.get("metadataJson"), dict) else {}
    task_profile = str(metadata.get("taskProfile") or DEFAULT_TASK_PROFILE).strip() or DEFAULT_TASK_PROFILE
    if task_profile not in AI_TASK_KEYS:
        task_profile = DEFAULT_TASK_PROFILE
    runtime = runtime_snapshot_from_record(ensure_runtime_config(db))
    profile = runtime.profile_for_task(task_profile)

    started = perf_counter()
    if llm_client.is_enabled(profile):
        output = llm_client.complete(profile, _build_system_prompt(normalized), test_input)
    else:
        output = (
            "Skill test could not call a live model because the selected runtime task profile is not configured. "
            "Set the provider and model in Settings, then test again."
        )
    latency_ms = int((perf_counter() - started) * 1000)

    result = {
        "id": f"skill-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "input": test_input,
        "output": output or "",
        "taskProfile": task_profile,
        "provider": profile.provider,
        "model": profile.model,
        "success": bool(output),
        "actor": actor,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "latencyMs": latency_ms,
    }

    history = metadata.get("testHistory")
    if not isinstance(history, list):
        history = []
    history.append(result)
    metadata["testHistory"] = history[-10:]
    metadata["lastTest"] = result
    manifest["metadataJson"] = metadata
    _append_review_event(manifest, event_type="test", actor=actor, comment=f"Ran skill test using {task_profile}")
    updated = _write_manifest(path, manifest)
    return {"skill": updated, "result": result}
