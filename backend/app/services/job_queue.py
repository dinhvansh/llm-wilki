from __future__ import annotations

import json

import redis
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job
from app.services.jobs import create_job


QUEUE_NAME = "llmwiki:source-jobs"


def _redis_client():
    if settings.JOB_QUEUE_BACKEND != "redis":
        return None
    try:
        return redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        return None


def notify_worker(job: Job) -> bool:
    client = _redis_client()
    if client is None:
        return False
    try:
        client.lpush(QUEUE_NAME, json.dumps({"jobId": job.id, "inputRef": job.input_ref, "jobType": job.job_type}))
        return True
    except redis.RedisError:
        return False


def enqueue_source_job(
    db: Session,
    *,
    job_type: str,
    source_id: str,
    actor: str,
    logs: list[str] | None = None,
    retry_of_job_id: str | None = None,
    attempt: int = 1,
    max_attempts: int | None = None,
) -> Job:
    job = create_job(
        db,
        job_type=job_type,
        input_ref=source_id,
        status="pending",
        logs=logs or [],
        actor=actor,
        retry_of_job_id=retry_of_job_id,
        attempt=attempt,
        max_attempts=max_attempts or settings.JOB_MAX_ATTEMPTS,
    )
    notified = notify_worker(job)
    if not notified:
        job.logs_json = [*(job.logs_json or []), "Queued in database; Redis notification unavailable or disabled"]
        db.commit()
        db.refresh(job)
    return job
