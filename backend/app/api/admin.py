from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_roles
from app.core.observability import duration_ms, percentile
from app.db.database import get_db
from app.models import AuditLog, Department, Job, Source, User
from app.services.audit import serialize_audit_log
from app.services.audit import create_audit_log
from app.services.auth import Actor, actor_metadata, hash_password, serialize_user
from app.services.job_queue import notify_worker
from app.services.jobs import retry_job, serialize_job
from app.services.quality_runs import list_eval_runs
from app.services.settings import (
    merge_runtime_settings_import,
    redact_runtime_settings_payload,
    serialize_runtime_settings,
    update_runtime_settings,
)
from app.services.permissions import ROLE_PERMISSION_MATRIX

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
EVAL_REPORT_JSON = ROOT / "evals" / "last_eval_report.json"
BENCHMARK_REPORT_JSON = ROOT / "evals" / "last_benchmark_report.json"


class BulkRetryPayload(BaseModel):
    jobIds: list[str] | None = None
    limit: int = 20


class ConfigImportPayload(BaseModel):
    settings: dict


class AdminUserCreatePayload(BaseModel):
    email: str
    name: str
    role: str = "reader"
    password: str
    departmentId: str | None = None
    isActive: bool = True


class AdminUserUpdatePayload(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    departmentId: str | None = None
    isActive: bool | None = None


class AdminUserPasswordPayload(BaseModel):
    password: str


class DepartmentPayload(BaseModel):
    name: str
    description: str = ""


class DepartmentUpdatePayload(BaseModel):
    name: str | None = None
    description: str | None = None


def _load_report(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _serialize_admin_user(db: Session, user: User) -> dict:
    payload = serialize_user(db, user)
    payload["isActive"] = bool(user.is_active)
    payload["createdAt"] = user.created_at.isoformat() if user.created_at else None
    payload["updatedAt"] = user.updated_at.isoformat() if user.updated_at else None
    return payload


def _serialize_department(department: Department) -> dict:
    return {
        "id": department.id,
        "name": department.name,
        "slug": department.slug,
        "description": department.description,
        "createdAt": department.created_at.isoformat() if department.created_at else None,
        "updatedAt": department.updated_at.isoformat() if department.updated_at else None,
    }


def _serialize_role(name: str, permissions: set[str]) -> dict:
    return {
        "id": name,
        "name": name.title(),
        "slug": name,
        "description": {
            "reader": "Browse and ask against allowed knowledge.",
            "editor": "Edit sources, pages, and structured knowledge assets.",
            "reviewer": "Review, approve, and govern knowledge workflows.",
            "admin": "Full system access, settings, and people management.",
        }.get(name, ""),
        "permissions": sorted(permissions),
        "isSystem": True,
    }


def _slugify_department(name: str) -> str:
    return "-".join(part for part in "".join(char.lower() if char.isalnum() else "-" for char in name).split("-") if part)


@router.get("/operations")
async def operations_dashboard(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    jobs = db.query(Job).order_by(Job.started_at.desc()).limit(500).all()
    durations = [value for value in (duration_ms(job.started_at, job.finished_at) for job in jobs) if value is not None]
    status_counts = Counter(job.status for job in jobs)
    type_counts = Counter(job.job_type for job in jobs)
    failed_jobs = [job for job in jobs if job.status == "failed"]
    source_counts = Counter(source.ingest_status for source in db.query(Source).all())
    stage_counts: Counter[str] = Counter()
    for job in jobs:
        for step in job.steps_json or []:
            stage_counts[str(step.get("name") or "unknown")] += 1
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "jobMetrics": {
            "total": len(jobs),
            "byStatus": dict(status_counts),
            "byType": dict(type_counts),
            "pending": status_counts.get("pending", 0),
            "running": status_counts.get("running", 0),
            "failed": status_counts.get("failed", 0),
            "durationMs": {
                "p50": percentile(durations, 50),
                "p95": percentile(durations, 95),
                "max": max(durations) if durations else None,
            },
            "stageCounts": dict(stage_counts),
        },
        "llmMetrics": {
            "runtime": {
                "answerProvider": serialize_runtime_settings(db)["answerProvider"],
                "ingestProvider": serialize_runtime_settings(db)["ingestProvider"],
                "embeddingProvider": serialize_runtime_settings(db)["embeddingProvider"],
                "taskProfiles": {
                    task: {
                        "provider": profile.get("provider"),
                        "model": profile.get("model"),
                    }
                    for task, profile in serialize_runtime_settings(db)["aiTaskProfiles"].items()
                },
            },
            "note": "Provider token/latency counters are exposed when provider clients return usage metadata.",
        },
        "retrievalMetrics": {
            "diagnosticsAvailable": True,
            "note": "Ask/search responses include per-query retrieval diagnostics; aggregate persistence is a future extension.",
        },
        "sourceThroughput": {
            "byIngestStatus": dict(source_counts),
            "processedSources": source_counts.get("indexed", 0) + source_counts.get("completed", 0),
        },
        "failedJobDrilldown": [serialize_job(job) for job in failed_jobs[:20]],
    }


@router.get("/quality")
async def quality_dashboard(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    eval_report = _load_report(EVAL_REPORT_JSON)
    benchmark_report = _load_report(BENCHMARK_REPORT_JSON)

    behavior_cases = list((eval_report or {}).get("behaviorCases") or [])
    failed_behavior_cases = [item for item in behavior_cases if not item.get("success")]
    failed_quality_gates = [
        {"name": name, "passed": passed}
        for name, passed in ((eval_report or {}).get("qualityGates") or {}).items()
        if name != "allPassed" and not bool(passed)
    ]
    failed_benchmark_gates = [
        {"name": name, "passed": passed}
        for name, passed in ((benchmark_report or {}).get("qualityGates") or {}).items()
        if name != "allPassed" and not bool(passed)
    ]

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "evalReportAvailable": eval_report is not None,
        "benchmarkReportAvailable": benchmark_report is not None,
        "evalReport": eval_report,
        "benchmarkReport": benchmark_report,
        "summary": {
            "evalSuccess": bool((eval_report or {}).get("success")),
            "benchmarkSuccess": bool((benchmark_report or {}).get("success")),
            "failedBehaviorCases": len(failed_behavior_cases),
            "failedEvalGates": len(failed_quality_gates),
            "failedBenchmarkGates": len(failed_benchmark_gates),
        },
        "failedBehaviorCases": failed_behavior_cases,
        "failedEvalGates": failed_quality_gates,
        "failedBenchmarkGates": failed_benchmark_gates,
        "recentRuns": list_eval_runs(db, limit=12),
        "commands": {
            "eval": "python backend\\scripts\\evaluate_quality.py",
            "benchmark": "python backend\\scripts\\benchmark_retrieval.py",
            "regression": "powershell -ExecutionPolicy Bypass -File .\\scripts\\run_regression.ps1 -SkipDocker -SkipE2E",
        },
    }


@router.get("/audit")
async def global_audit_log(action: str | None = None, objectType: str | None = None, actorName: str | None = None, limit: int = 100, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if objectType:
        query = query.filter(AuditLog.object_type == objectType)
    if actorName:
        query = query.filter(AuditLog.actor.ilike(f"%{actorName.strip()}%"))
    return [serialize_audit_log(row) for row in query.order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500))).all()]


@router.post("/jobs/bulk-retry")
async def bulk_retry_failed_jobs(payload: BulkRetryPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    query = db.query(Job).filter(Job.status == "failed", Job.job_type.in_(["ingest", "rebuild"]))
    if payload.jobIds:
        query = query.filter(Job.id.in_(payload.jobIds))
    jobs = query.order_by(Job.started_at.desc()).limit(max(1, min(payload.limit, 100))).all()
    retried = []
    skipped = []
    for job in jobs:
        retry = retry_job(db, job.id, actor=actor.name)
        if retry:
            notify_worker(retry)
            retried.append(serialize_job(retry))
        else:
            skipped.append(job.id)
    return {"success": True, "retriedCount": len(retried), "retried": retried, "skippedIds": skipped}


@router.get("/config/export")
async def export_config(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    settings = serialize_runtime_settings(db)
    return {"version": 2, "exportedAt": datetime.now(timezone.utc).isoformat(), "settings": redact_runtime_settings_payload(settings)}


@router.post("/config/import")
async def import_config(payload: ConfigImportPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    current = serialize_runtime_settings(db)
    merged = merge_runtime_settings_import(current, payload.settings)
    try:
        return {"success": True, "settings": update_runtime_settings(db, merged, actor_name=actor.name)}
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing setting {exc}") from exc


@router.get("/departments")
async def list_departments(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    return [_serialize_department(item) for item in db.query(Department).order_by(Department.name.asc()).all()]


@router.post("/departments")
async def create_department(payload: DepartmentPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    name = " ".join(payload.name.split()).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name is required")
    slug = _slugify_department(name)
    if not slug:
        raise HTTPException(status_code=400, detail="Department slug is invalid")
    if db.query(Department.id).filter((Department.name == name) | (Department.slug == slug)).first():
        raise HTTPException(status_code=409, detail="Department already exists")
    now = datetime.now(timezone.utc)
    department = Department(
        id=f"dept-{uuid4().hex[:12]}",
        name=name,
        slug=slug,
        description=payload.description.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(department)
    create_audit_log(
        db,
        action="create_department",
        object_type="department",
        object_id=department.id,
        actor=actor.name,
        summary=f"Created department `{department.name}`",
        metadata=actor_metadata(actor),
    )
    db.commit()
    db.refresh(department)
    return _serialize_department(department)


@router.patch("/departments/{department_id}")
async def update_department(department_id: str, payload: DepartmentUpdatePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    changes: dict[str, object] = {}
    if payload.name is not None:
        name = " ".join(payload.name.split()).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Department name is required")
        slug = _slugify_department(name)
        existing = db.query(Department.id).filter(Department.id != department.id, ((Department.name == name) | (Department.slug == slug))).first()
        if existing:
            raise HTTPException(status_code=409, detail="Department already exists")
        department.name = name
        department.slug = slug
        changes["name"] = name
        changes["slug"] = slug
    if payload.description is not None:
        department.description = payload.description.strip()
        changes["description"] = department.description

    department.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="update_department",
        object_type="department",
        object_id=department.id,
        actor=actor.name,
        summary=f"Updated department `{department.name}`",
        metadata={**actor_metadata(actor), "changes": changes},
    )
    db.commit()
    db.refresh(department)
    return _serialize_department(department)


@router.get("/roles")
async def list_roles(actor: Actor = Depends(require_roles("admin"))):
    return [_serialize_role(name, permissions) for name, permissions in ROLE_PERMISSION_MATRIX.items()]


@router.get("/users")
async def list_users(db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [_serialize_admin_user(db, user) for user in users]


@router.post("/users")
async def create_user(payload: AdminUserCreatePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    email = payload.email.lower().strip()
    name = " ".join(payload.name.split()).strip()
    password = payload.password.strip()
    role = (payload.role or "reader").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if role not in {"reader", "editor", "reviewer", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="User email already exists")
    department_id = payload.departmentId.strip() if isinstance(payload.departmentId, str) and payload.departmentId.strip() else None
    if department_id and not db.query(Department.id).filter(Department.id == department_id).first():
        raise HTTPException(status_code=400, detail="Department not found")

    now = datetime.now(timezone.utc)
    user = User(
        id=f"user-{uuid4().hex[:12]}",
        email=email,
        name=name,
        role=role,
        department_id=department_id,
        password_hash=hash_password(password),
        is_active=bool(payload.isActive),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    create_audit_log(
        db,
        action="create_user",
        object_type="user",
        object_id=user.id,
        actor=actor.name,
        summary=f"Created user `{user.email}` with role `{user.role}`",
        metadata={**actor_metadata(actor), "userEmail": user.email, "userRole": user.role, "isActive": user.is_active, "departmentId": user.department_id},
    )
    db.commit()
    db.refresh(user)
    return _serialize_admin_user(db, user)


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: AdminUserUpdatePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes: dict[str, object] = {}
    if payload.email is not None:
        email = payload.email.lower().strip()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Valid email is required")
        existing = db.query(User.id).filter(User.email == email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="User email already exists")
        user.email = email
        changes["email"] = email
    if payload.name is not None:
        name = " ".join(payload.name.split()).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Name is required")
        user.name = name
        changes["name"] = name
    if payload.role is not None:
        role = payload.role.strip().lower()
        if role not in {"reader", "editor", "reviewer", "admin"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
        changes["role"] = role
    if payload.departmentId is not None:
        department_id = payload.departmentId.strip() if payload.departmentId and payload.departmentId.strip() else None
        if department_id and not db.query(Department.id).filter(Department.id == department_id).first():
            raise HTTPException(status_code=400, detail="Department not found")
        user.department_id = department_id
        changes["departmentId"] = department_id
    if payload.isActive is not None:
        user.is_active = bool(payload.isActive)
        changes["isActive"] = user.is_active

    user.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="update_user",
        object_type="user",
        object_id=user.id,
        actor=actor.name,
        summary=f"Updated user `{user.email}`",
        metadata={**actor_metadata(actor), "changes": changes},
    )
    db.commit()
    db.refresh(user)
    return _serialize_admin_user(db, user)


@router.post("/users/{user_id}/set-password")
async def set_user_password(user_id: str, payload: AdminUserPasswordPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    password = payload.password.strip()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.password_hash = hash_password(password)
    user.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="set_user_password",
        object_type="user",
        object_id=user.id,
        actor=actor.name,
        summary=f"Reset password for user `{user.email}`",
        metadata=actor_metadata(actor),
    )
    db.commit()
    db.refresh(user)
    return {"success": True, "user": _serialize_admin_user(db, user)}
