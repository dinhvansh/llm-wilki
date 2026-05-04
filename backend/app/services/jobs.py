from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import Job


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def job_step(name: str, status: str, progress: int | None = None, details: dict | None = None) -> dict:
    return {
        "name": name,
        "status": status,
        "progress": progress,
        "details": details or {},
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_steps(steps: list[dict] | None) -> list[dict]:
    normalized = []
    for step in steps or []:
        normalized.append(
            {
                "name": str(step.get("name") or "step"),
                "status": str(step.get("status") or "pending"),
                "progress": step.get("progress"),
                "details": dict(step.get("details") or {}),
                "updatedAt": step.get("updatedAt") or datetime.now(timezone.utc).isoformat(),
            }
        )
    return normalized


def serialize_job(job: Job) -> dict:
    return {
        "id": job.id,
        "jobType": job.job_type,
        "status": job.status,
        "startedAt": _iso(job.started_at),
        "finishedAt": _iso(job.finished_at),
        "inputRef": job.input_ref,
        "outputRef": job.output_ref,
        "errorMessage": job.error_message,
        "logsJson": job.logs_json or [],
        "stepsJson": _normalize_steps(job.steps_json),
        "progressPercent": job.progress_percent or 0,
        "actor": job.actor or "System",
        "retryOfJobId": job.retry_of_job_id,
        "attempt": job.attempt or 1,
        "maxAttempts": job.max_attempts or 3,
        "heartbeatAt": _iso(job.heartbeat_at),
        "cancelRequested": bool(job.cancel_requested),
    }


def create_job(
    db: Session,
    job_type: str,
    input_ref: str,
    status: str = "pending",
    logs: list[str] | None = None,
    *,
    actor: str = "System",
    steps: list[dict] | None = None,
    progress_percent: int = 0,
    retry_of_job_id: str | None = None,
    attempt: int = 1,
    max_attempts: int = 3,
) -> Job:
    job = Job(
        id=f"job-{uuid4().hex[:8]}",
        job_type=job_type,
        status=status,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        input_ref=input_ref,
        output_ref=None,
        error_message=None,
        logs_json=logs or [],
        steps_json=steps or [job_step("queued", status, progress_percent, {"inputRef": input_ref})],
        progress_percent=max(0, min(progress_percent, 100)),
        actor=actor,
        retry_of_job_id=retry_of_job_id,
        attempt=max(1, attempt),
        max_attempts=max(1, max_attempts),
        heartbeat_at=None,
        cancel_requested=False,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(
    db: Session,
    job_id: str,
    *,
    status: str | None = None,
    output_ref: str | None = None,
    error_message: str | None = None,
    append_logs: list[str] | None = None,
    steps: list[dict] | None = None,
    append_steps: list[dict] | None = None,
    progress_percent: int | None = None,
    heartbeat: bool = False,
    cancel_requested: bool | None = None,
    finished: bool = False,
) -> Job | None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None
    if status:
        job.status = status
    if output_ref is not None:
        job.output_ref = output_ref
    if error_message is not None:
        job.error_message = error_message
    if append_logs:
        job.logs_json = [*(job.logs_json or []), *append_logs]
    if steps is not None:
        job.steps_json = _normalize_steps(steps)
    if append_steps:
        job.steps_json = [*_normalize_steps(job.steps_json), *_normalize_steps(append_steps)]
    if progress_percent is not None:
        job.progress_percent = max(0, min(progress_percent, 100))
    if heartbeat:
        job.heartbeat_at = datetime.now(timezone.utc)
    if cancel_requested is not None:
        job.cancel_requested = cancel_requested
    if finished:
        job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def list_jobs(db: Session, status: str | None = None, job_type: str | None = None, limit: int = 50) -> list[dict]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if job_type:
        query = query.filter(Job.job_type == job_type)
    return [serialize_job(job) for job in query.order_by(Job.started_at.desc()).limit(limit).all()]


def list_jobs_for_input(db: Session, input_ref: str, limit: int = 20) -> list[dict]:
    jobs = db.query(Job).filter(Job.input_ref == input_ref).order_by(Job.started_at.desc()).limit(limit).all()
    return [serialize_job(job) for job in jobs]


def get_job(db: Session, job_id: str) -> dict | None:
    job = db.query(Job).filter(Job.id == job_id).first()
    return serialize_job(job) if job else None


def cancel_job(db: Session, job_id: str) -> dict | None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None
    if job.status not in {"pending", "running"}:
        return serialize_job(job)
    if job.status == "pending":
        job.status = "canceled"
        job.finished_at = datetime.now(timezone.utc)
        job.logs_json = [*(job.logs_json or []), "Pending job canceled by user"]
        job.steps_json = [
            *_normalize_steps(job.steps_json),
            job_step("cancel", "canceled", job.progress_percent or 0, {"reason": "Canceled before worker pickup"}),
        ]
    else:
        job.cancel_requested = True
        job.logs_json = [*(job.logs_json or []), "Cancel requested for running job"]
        job.steps_json = [
            *_normalize_steps(job.steps_json),
            job_step("cancel_requested", "running", job.progress_percent or 0, {"reason": "Worker will stop at next cooperative checkpoint"}),
        ]
    db.commit()
    db.refresh(job)
    return serialize_job(job)


def retry_job(db: Session, job_id: str, actor: str | None = None) -> Job | None:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.status != "failed" or job.job_type not in {"ingest", "rebuild"}:
        return None
    if (job.attempt or 1) >= (job.max_attempts or 3):
        return None
    return create_job(
        db,
        job_type=job.job_type,
        input_ref=job.input_ref,
        status="pending",
        logs=[f"Retry requested from {job.id}"],
        actor=actor or job.actor or "System",
        steps=[job_step("queued", "pending", 0, {"retryOf": job.id, "inputRef": job.input_ref, "attempt": (job.attempt or 1) + 1})],
        retry_of_job_id=job.id,
        attempt=(job.attempt or 1) + 1,
        max_attempts=job.max_attempts or 3,
    )


def claim_next_source_job(db: Session) -> Job | None:
    job = (
        db.query(Job)
        .filter(Job.status == "pending", Job.job_type.in_(["ingest", "rebuild"]))
        .order_by(Job.started_at.asc())
        .first()
    )
    if not job:
        return None
    job.status = "running"
    job.heartbeat_at = datetime.now(timezone.utc)
    job.logs_json = [*(job.logs_json or []), "Worker claimed job"]
    job.steps_json = [*_normalize_steps(job.steps_json), job_step("worker_claim", "running", job.progress_percent or 0, {"worker": "source-worker"})]
    db.commit()
    db.refresh(job)
    return job


def _steps_from_source_metadata(result: dict, final_status: str) -> list[dict]:
    stage_rows = list((result.get("metadataJson") or {}).get("pipelineStages") or [])
    if not stage_rows:
        return [job_step("process_source", final_status, 100 if final_status == "completed" else 0, {"sourceId": result.get("id")})]
    total = len(stage_rows)
    steps = []
    for index, row in enumerate(stage_rows, start=1):
        progress = int((index / max(total, 1)) * 90) + 5
        steps.append(
            job_step(
                str(row.get("name") or f"stage_{index}"),
                str(row.get("status") or final_status),
                min(progress, 95),
                dict(row.get("details") or {}),
            )
        )
    if final_status == "completed":
        steps.append(job_step("persist_index", "completed", 100, {"sourceId": result.get("id"), "parseStatus": result.get("parseStatus")}))
    return steps


def run_source_processing_job(job_id: str, source_id: str) -> None:
    from app.services.sources import ingest_source

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status == "canceled":
            return
        if job.cancel_requested:
            update_job(db, job_id, status="canceled", append_logs=["Job stopped before processing because cancel was requested"], finished=True)
            return
        update_job(
            db,
            job_id,
            append_logs=["Parsing source", "Chunking and extracting claims"],
            append_steps=[job_step("process_source", "running", 10, {"sourceId": source_id})],
            progress_percent=10,
            heartbeat=True,
        )
        result = ingest_source(db, source_id)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.cancel_requested:
            update_job(db, job_id, status="canceled", append_logs=["Job completed processing but was marked canceled by user request"], progress_percent=100, finished=True)
            return
        if result and result["parseStatus"] != "failed":
            update_job(
                db,
                job_id,
                status="completed",
                output_ref=source_id,
                append_logs=["Source indexed", "Review item created"],
                steps=_steps_from_source_metadata(result, "completed"),
                progress_percent=100,
                finished=True,
            )
        else:
            update_job(
                db,
                job_id,
                status="failed",
                output_ref=source_id,
                error_message="Ingest pipeline failed",
                append_logs=["Source processing failed"],
                steps=_steps_from_source_metadata(result or {"id": source_id}, "failed"),
                progress_percent=100,
                finished=True,
            )
    except Exception as exc:
        update_job(
            db,
            job_id,
            status="failed",
            output_ref=source_id,
            error_message=str(exc),
            append_logs=["Unhandled background task error"],
            append_steps=[job_step("process_source", "failed", 100, {"error": str(exc)})],
            progress_percent=100,
            finished=True,
        )
    finally:
        db.close()
