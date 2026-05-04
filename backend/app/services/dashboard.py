from __future__ import annotations

from collections import Counter
from datetime import timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Claim, Entity, Job, Page, ReviewItem, Source, SourceChunk


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def get_dashboard_stats(db: Session) -> dict:
    total_sources = db.query(func.count(Source.id)).scalar() or 0
    total_pages = db.query(func.count(Page.id)).scalar() or 0
    total_chunks = db.query(func.count(SourceChunk.id)).scalar() or 0
    total_entities = db.query(func.count(Entity.id)).scalar() or 0
    unverified_claims = db.query(func.count(Claim.id)).filter(Claim.canonical_status == "unverified").scalar() or 0
    review_queue_count = db.query(func.count(ReviewItem.id)).scalar() or 0
    failed_jobs = db.query(Job).filter(Job.status == "failed").order_by(Job.started_at.desc()).all()

    page_status_breakdown = {status: count for status, count in db.query(Page.status, func.count(Page.id)).group_by(Page.status).all()}
    source_type_breakdown = {source_type: count for source_type, count in db.query(Source.source_type, func.count(Source.id)).group_by(Source.source_type).all()}

    published_series = Counter()
    for published_at, in db.query(Page.published_at).filter(Page.published_at.is_not(None)).all():
        published_series[published_at.date().isoformat()] += 1

    recent_activity = []
    for source in db.query(Source).order_by(Source.uploaded_at.desc()).limit(3).all():
        recent_activity.append(
            {
                "id": f"act-source-{source.id}",
                "type": "source_uploaded",
                "description": f"{source.title} uploaded",
                "entityId": source.id,
                "entityTitle": source.title,
                "timestamp": _iso(source.uploaded_at),
                "user": source.created_by,
            }
        )
    for page in db.query(Page).filter(Page.published_at.is_not(None)).order_by(Page.published_at.desc()).limit(3).all():
        recent_activity.append(
            {
                "id": f"act-page-{page.id}",
                "type": "page_published",
                "description": f'"{page.title}" page was published',
                "entityId": page.id,
                "entityTitle": page.title,
                "timestamp": _iso(page.published_at),
                "user": page.owner,
            }
        )
    for job in failed_jobs[:3]:
        recent_activity.append(
            {
                "id": f"act-job-{job.id}",
                "type": "job_failed",
                "description": job.error_message or f"{job.job_type} job failed",
                "entityId": job.id,
                "entityTitle": job.id,
                "timestamp": _iso(job.started_at),
                "user": None,
            }
        )

    all_timestamps = [value for (value,) in db.query(Source.updated_at).all()] + [value for (value,) in db.query(Page.last_composed_at).all()] + [value for (value,) in db.query(Job.started_at).all()]

    return {
        "totalSources": total_sources,
        "totalPages": total_pages,
        "publishedPages": page_status_breakdown.get("published", 0),
        "draftPages": page_status_breakdown.get("draft", 0),
        "inReviewPages": page_status_breakdown.get("in_review", 0),
        "stalePages": page_status_breakdown.get("stale", 0),
        "unverifiedClaims": unverified_claims,
        "reviewQueueCount": review_queue_count,
        "lastSyncTime": max(all_timestamps).isoformat() if all_timestamps else "",
        "failedJobsCount": len(failed_jobs),
        "totalChunks": total_chunks,
        "totalEntities": total_entities,
        "sourceTypeBreakdown": source_type_breakdown,
        "pageStatusBreakdown": page_status_breakdown,
        "pagesPublishedOverTime": [{"date": key, "value": value, "label": key[5:]} for key, value in sorted(published_series.items())],
        "recentActivity": sorted(recent_activity, key=lambda item: item["timestamp"], reverse=True)[:7],
        "failedJobs": [
            {"id": job.id, "jobType": job.job_type, "status": job.status, "startedAt": _iso(job.started_at), "finishedAt": _iso(job.finished_at), "inputRef": job.input_ref, "outputRef": job.output_ref, "errorMessage": job.error_message, "logsJson": job.logs_json}
            for job in failed_jobs
        ],
    }
