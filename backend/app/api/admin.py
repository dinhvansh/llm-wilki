from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_roles
from app.core.observability import duration_ms, percentile
from app.db.database import get_db
from app.models import AuditLog, Job, Source
from app.services.audit import serialize_audit_log
from app.services.auth import Actor
from app.services.job_queue import notify_worker
from app.services.jobs import retry_job, serialize_job
from app.services.settings import (
    merge_runtime_settings_import,
    redact_runtime_settings_payload,
    serialize_runtime_settings,
    update_runtime_settings,
)

router = APIRouter()


class BulkRetryPayload(BaseModel):
    jobIds: list[str] | None = None
    limit: int = 20


class ConfigImportPayload(BaseModel):
    settings: dict


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
