from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import AuditLog


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def create_audit_log(
    db: Session,
    *,
    action: str,
    object_type: str,
    object_id: str,
    actor: str,
    summary: str,
    metadata: dict | None = None,
) -> AuditLog:
    record = AuditLog(
        id=f"audit-{uuid4().hex[:8]}",
        action=action,
        object_type=object_type,
        object_id=object_id,
        actor=actor,
        summary=summary[:255],
        metadata_json=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.flush()
    return record


def serialize_audit_log(record: AuditLog) -> dict:
    return {
        "id": record.id,
        "action": record.action,
        "objectType": record.object_type,
        "objectId": record.object_id,
        "actor": record.actor,
        "summary": record.summary,
        "metadataJson": record.metadata_json or {},
        "createdAt": _iso(record.created_at),
    }


def list_audit_logs(db: Session, object_type: str | None = None, object_id: str | None = None, limit: int = 50) -> list[dict]:
    query = db.query(AuditLog)
    if object_type:
        query = query.filter(AuditLog.object_type == object_type)
    if object_id:
        query = query.filter(AuditLog.object_id == object_id)
    return [serialize_audit_log(record) for record in query.order_by(AuditLog.created_at.desc()).limit(limit).all()]
