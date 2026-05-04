from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Collection, Entity, Page, PageSourceLink, Source, SourceEntityLink, SourceSuggestion
from app.services.audit import create_audit_log


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_suggestion(suggestion: SourceSuggestion) -> dict:
    return {
        "id": suggestion.id,
        "sourceId": suggestion.source_id,
        "suggestionType": suggestion.suggestion_type,
        "targetType": suggestion.target_type,
        "targetId": suggestion.target_id,
        "targetLabel": suggestion.target_label,
        "status": suggestion.status,
        "confidenceScore": suggestion.confidence_score,
        "reason": suggestion.reason,
        "evidence": suggestion.evidence_json or [],
        "createdAt": _iso(suggestion.created_at),
        "decidedAt": _iso(suggestion.decided_at),
    }


def list_source_suggestions(db: Session, source_id: str) -> list[dict]:
    items = (
        db.query(SourceSuggestion)
        .filter(SourceSuggestion.source_id == source_id)
        .order_by(SourceSuggestion.status.asc(), SourceSuggestion.confidence_score.desc(), SourceSuggestion.created_at.desc())
        .all()
    )
    return [serialize_suggestion(item) for item in items]


def create_source_suggestion(
    db: Session,
    *,
    source_id: str,
    suggestion_type: str,
    target_type: str,
    target_id: str | None,
    target_label: str,
    confidence_score: float,
    reason: str,
    evidence: list[dict] | None = None,
    status: str = "pending",
) -> SourceSuggestion:
    suggestion = SourceSuggestion(
        id=f"sug-{uuid4().hex[:8]}",
        source_id=source_id,
        suggestion_type=suggestion_type,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        status=status,
        confidence_score=confidence_score,
        reason=reason,
        evidence_json=evidence or [],
        created_at=datetime.now(timezone.utc),
        decided_at=datetime.now(timezone.utc) if status != "pending" else None,
    )
    db.add(suggestion)
    return suggestion


def _resolve_target_label(db: Session, target_type: str, target_id: str | None) -> str:
    if not target_id:
        return "Standalone"
    if target_type == "collection":
        target = db.query(Collection).filter(Collection.id == target_id).first()
        return target.name if target else target_id
    if target_type == "page":
        target = db.query(Page).filter(Page.id == target_id).first()
        return target.title if target else target_id
    if target_type == "entity":
        target = db.query(Entity).filter(Entity.id == target_id).first()
        return target.name if target else target_id
    return target_id


def change_suggestion_target(db: Session, suggestion_id: str, target_id: str | None) -> dict | None:
    suggestion = db.query(SourceSuggestion).filter(SourceSuggestion.id == suggestion_id).first()
    if not suggestion:
        return None
    suggestion.target_id = target_id
    suggestion.target_label = _resolve_target_label(db, suggestion.target_type, target_id)
    suggestion.status = "pending"
    suggestion.decided_at = None
    db.commit()
    db.refresh(suggestion)
    return serialize_suggestion(suggestion)


def accept_suggestion(db: Session, suggestion_id: str) -> dict | None:
    suggestion = db.query(SourceSuggestion).filter(SourceSuggestion.id == suggestion_id).first()
    if not suggestion:
        return None
    source = db.query(Source).filter(Source.id == suggestion.source_id).first()
    if not source:
        return None

    if suggestion.target_type == "collection" and suggestion.target_id:
        source.collection_id = suggestion.target_id
        page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id == source.id).all()]
        if page_ids:
            db.query(Page).filter(Page.id.in_(page_ids)).update({"collection_id": suggestion.target_id}, synchronize_session=False)
        create_audit_log(
            db,
            action="accept_collection_suggestion",
            object_type="source",
            object_id=source.id,
            actor="Current User",
            summary=f"Assigned source `{source.title}` to collection `{suggestion.target_label}`",
            metadata={"suggestionId": suggestion.id, "collectionId": suggestion.target_id, "affectedPageIds": page_ids},
        )

    if suggestion.target_type == "page" and suggestion.target_id:
        exists = (
            db.query(PageSourceLink)
            .filter(PageSourceLink.page_id == suggestion.target_id, PageSourceLink.source_id == source.id)
            .first()
        )
        if not exists:
            db.add(PageSourceLink(id=f"psl-{uuid4().hex[:8]}", page_id=suggestion.target_id, source_id=source.id))
        create_audit_log(
            db,
            action="accept_page_link_suggestion",
            object_type="page",
            object_id=suggestion.target_id,
            actor="Current User",
            summary=f"Linked source `{source.title}` from accepted ingest suggestion",
            metadata={"suggestionId": suggestion.id, "sourceId": source.id},
        )

    if suggestion.target_type == "entity" and suggestion.target_id:
        exists = (
            db.query(SourceEntityLink)
            .filter(SourceEntityLink.source_id == source.id, SourceEntityLink.entity_id == suggestion.target_id)
            .first()
        )
        if not exists:
            db.add(
                SourceEntityLink(
                    id=f"sel-{uuid4().hex[:8]}",
                    source_id=source.id,
                    entity_id=suggestion.target_id,
                    mention_count=1,
                    confidence_score=suggestion.confidence_score,
                )
            )
        create_audit_log(
            db,
            action="accept_entity_link_suggestion",
            object_type="source",
            object_id=source.id,
            actor="Current User",
            summary=f"Linked source `{source.title}` to entity `{suggestion.target_label}`",
            metadata={"suggestionId": suggestion.id, "entityId": suggestion.target_id},
        )

    suggestion.status = "accepted"
    suggestion.decided_at = datetime.now(timezone.utc)
    source.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(suggestion)
    return serialize_suggestion(suggestion)


def reject_suggestion(db: Session, suggestion_id: str) -> dict | None:
    suggestion = db.query(SourceSuggestion).filter(SourceSuggestion.id == suggestion_id).first()
    if not suggestion:
        return None
    suggestion.status = "rejected"
    suggestion.decided_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="reject_source_suggestion",
        object_type="source",
        object_id=suggestion.source_id,
        actor="Current User",
        summary=f"Rejected {suggestion.suggestion_type.replace('_', ' ')} suggestion",
        metadata={"suggestionId": suggestion.id, "targetType": suggestion.target_type, "targetId": suggestion.target_id},
    )
    db.commit()
    db.refresh(suggestion)
    return serialize_suggestion(suggestion)


def accept_pending_suggestions(db: Session, source_id: str) -> dict | None:
    if not db.query(Source).filter(Source.id == source_id).first():
        return None
    suggestions = (
        db.query(SourceSuggestion)
        .filter(SourceSuggestion.source_id == source_id, SourceSuggestion.status == "pending")
        .order_by(SourceSuggestion.confidence_score.desc())
        .all()
    )
    accepted: list[dict] = []
    for suggestion in suggestions:
        result = accept_suggestion(db, suggestion.id)
        if result:
            accepted.append(result)
    return {"sourceId": source_id, "acceptedCount": len(accepted), "suggestions": accepted}


def reject_pending_suggestions(db: Session, source_id: str) -> dict | None:
    if not db.query(Source).filter(Source.id == source_id).first():
        return None
    now = datetime.now(timezone.utc)
    suggestions = (
        db.query(SourceSuggestion)
        .filter(SourceSuggestion.source_id == source_id, SourceSuggestion.status == "pending")
        .all()
    )
    for suggestion in suggestions:
        suggestion.status = "rejected"
        suggestion.decided_at = now
    db.commit()
    return {"sourceId": source_id, "rejectedCount": len(suggestions), "suggestions": [serialize_suggestion(item) for item in suggestions]}


def set_source_standalone(db: Session, source_id: str) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    source.collection_id = None
    source.updated_at = datetime.now(timezone.utc)
    for suggestion in db.query(SourceSuggestion).filter(SourceSuggestion.source_id == source_id, SourceSuggestion.status == "pending").all():
        if suggestion.target_type in {"collection", "page"}:
            suggestion.status = "rejected"
            suggestion.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"sourceId": source_id, "collectionId": None}
