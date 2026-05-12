from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import EvalRun


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _extract_summary(run_type: str, report: dict) -> tuple[int, dict, dict]:
    if run_type == "eval":
        case_count = int(report.get("caseCount") or 0) + int(report.get("behaviorCaseCount") or 0)
        summary = {
            "caseCount": report.get("caseCount"),
            "behaviorCaseCount": report.get("behaviorCaseCount"),
            "averages": report.get("averages") or {},
            "behaviorMetrics": report.get("behaviorMetrics") or {},
        }
        quality_gates = report.get("qualityGates") or {}
        return case_count, summary, quality_gates

    if run_type == "benchmark":
        case_count = int(report.get("queryCount") or 0)
        summary = {
            "queryCount": report.get("queryCount"),
            "search": report.get("search") or [],
            "ask": report.get("ask") or [],
            "authorityBeforeAfter": report.get("authorityBeforeAfter") or {},
            "sectionSummarySignal": report.get("sectionSummarySignal") or {},
        }
        quality_gates = report.get("qualityGates") or {}
        return case_count, summary, quality_gates

    return 0, {}, {}


def create_eval_run(
    db: Session,
    *,
    run_type: str,
    run_name: str,
    version: str,
    report: dict,
    tags: list[str] | None = None,
    created_by: str = "system",
) -> EvalRun:
    case_count, summary, quality_gates = _extract_summary(run_type, report)
    run = EvalRun(
        id=f"evalrun-{uuid4().hex[:12]}",
        run_type=run_type,
        run_name=run_name,
        version=version or "",
        status="completed",
        success=bool(report.get("success")),
        case_count=case_count,
        summary_json=summary,
        quality_gates_json=quality_gates,
        tags_json=tags or [],
        report_json=report,
        created_by=created_by,
        created_at=_now(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def serialize_eval_run(run: EvalRun) -> dict:
    return {
        "id": run.id,
        "runType": run.run_type,
        "runName": run.run_name,
        "version": run.version,
        "status": run.status,
        "success": run.success,
        "caseCount": run.case_count,
        "summary": run.summary_json or {},
        "qualityGates": run.quality_gates_json or {},
        "tags": run.tags_json or [],
        "createdBy": run.created_by,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
    }


def list_eval_runs(db: Session, run_type: str | None = None, limit: int = 20) -> list[dict]:
    query = db.query(EvalRun)
    if run_type:
        query = query.filter(EvalRun.run_type == run_type)
    runs = query.order_by(EvalRun.created_at.desc()).limit(max(1, min(limit, 100))).all()
    return [serialize_eval_run(run) for run in runs]
