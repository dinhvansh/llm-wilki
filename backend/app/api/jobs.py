from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_roles
from app.services.auth import Actor
from app.schemas.dashboard import JobOut
from app.services.job_queue import notify_worker
from app.services.jobs import cancel_job, get_job, list_jobs, retry_job, serialize_job

router = APIRouter()


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs_route(status: str | None = None, jobType: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    return list_jobs(db, status=status, job_type=jobType, limit=limit)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
async def retry_job_route(job_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    job = retry_job(db, job_id, actor=actor.name)
    if not job:
        raise HTTPException(status_code=400, detail="Only failed ingest/rebuild jobs can be retried")
    notify_worker(job)
    return serialize_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job_route(job_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    job = cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
