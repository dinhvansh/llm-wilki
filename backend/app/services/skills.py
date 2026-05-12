from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
SKILL_PACKAGE_DIR = ROOT / "skill_packages"


def _package_paths() -> list[Path]:
    if not SKILL_PACKAGE_DIR.exists():
        return []
    return sorted(path for path in SKILL_PACKAGE_DIR.glob("*.json") if path.is_file())


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
    return {
        "id": package_id,
        "name": str(payload.get("name") or package_id).strip(),
        "version": str(payload.get("version") or "0.1.0").strip(),
        "scope": str(payload.get("scope") or "workspace").strip(),
        "status": str(payload.get("status") or "draft").strip(),
        "summary": str(payload.get("summary") or "").strip(),
        "description": str(payload.get("description") or "").strip(),
        "capabilities": [str(item).strip() for item in (payload.get("capabilities") or []) if str(item).strip()],
        "tags": [str(item).strip() for item in (payload.get("tags") or []) if str(item).strip()],
        "entryPoints": [str(item).strip() for item in (payload.get("entryPoints") or []) if str(item).strip()],
        "owner": str(payload.get("owner") or "").strip() or None,
        "reviewStatus": str(payload.get("reviewStatus") or "draft").strip(),
        "reviewHistory": payload.get("reviewHistory") if isinstance(payload.get("reviewHistory"), list) else [],
        "metadataJson": payload.get("metadataJson") if isinstance(payload.get("metadataJson"), dict) else {},
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
