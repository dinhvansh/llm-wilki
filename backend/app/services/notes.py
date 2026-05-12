from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Note, NoteAnchor, NoteVersion
from app.services.auth import Actor
from app.core.ingest import slugify
from app.models import ReviewItem
from app.services.pages import create_page_with_version
from app.services.permissions import can_access_collection_id

NOTE_SCOPES = {"private", "collection", "workspace"}
NOTE_STATUSES = {"active", "archived"}


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _clean_text(value: object, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split()).strip()
    if limit is not None:
        return text[:limit]
    return text


def _serialize_anchor(anchor: NoteAnchor) -> dict:
    return {
        "id": anchor.id,
        "noteId": anchor.note_id,
        "targetType": anchor.target_type,
        "targetId": anchor.target_id,
        "sourceId": anchor.source_id,
        "chunkId": anchor.chunk_id,
        "artifactId": anchor.artifact_id,
        "pageId": anchor.page_id,
        "sectionKey": anchor.section_key,
        "reviewItemId": anchor.review_item_id,
        "askMessageId": anchor.ask_message_id,
        "citationId": anchor.citation_id,
        "snippet": anchor.snippet,
        "metadataJson": anchor.metadata_json or {},
        "createdAt": _iso(anchor.created_at),
    }


def serialize_note(note: Note) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "body": note.body,
        "scope": note.scope,
        "status": note.status,
        "ownerId": note.owner_id,
        "ownerName": note.owner_name,
        "collectionId": note.collection_id,
        "tags": note.tags or [],
        "metadataJson": note.metadata_json or {},
        "anchors": [_serialize_anchor(anchor) for anchor in note.anchors],
        "createdAt": _iso(note.created_at),
        "updatedAt": _iso(note.updated_at),
        "archivedAt": _iso(note.archived_at),
    }


def _visible_query(db: Session, actor: Actor):
    query = db.query(Note).filter(Note.status != "archived")
    clauses = [Note.scope == "workspace"]
    if actor.id:
        clauses.append(Note.owner_id == actor.id)
    if actor.collection_scope_mode == "restricted":
        if actor.accessible_collection_ids:
            clauses.append(Note.collection_id.in_(list(actor.accessible_collection_ids)))
    else:
        clauses.append(Note.scope == "collection")
    return query.filter(or_(*clauses))


def list_notes(
    db: Session,
    actor: Actor,
    *,
    source_id: str | None = None,
    page_id: str | None = None,
    collection_id: str | None = None,
    search: str | None = None,
    limit: int = 50,
) -> list[dict]:
    query = _visible_query(db, actor)
    if collection_id:
        query = query.filter(Note.collection_id == collection_id)
    if source_id:
        query = query.join(NoteAnchor).filter(NoteAnchor.source_id == source_id)
    if page_id:
        query = query.join(NoteAnchor).filter(NoteAnchor.page_id == page_id)
    if search:
        lowered = f"%{search.lower()}%"
        query = query.filter(or_(Note.title.ilike(lowered), Note.body.ilike(lowered)))
    rows = query.order_by(Note.updated_at.desc()).limit(max(1, min(limit, 100))).all()
    return [serialize_note(row) for row in rows]


def get_note(db: Session, note_id: str, actor: Actor) -> dict | None:
    note = _visible_query(db, actor).filter(Note.id == note_id).first()
    return serialize_note(note) if note else None


def _validate_note_scope(actor: Actor, scope: str, collection_id: str | None) -> None:
    if scope not in NOTE_SCOPES:
        raise ValueError("scope must be one of: private, collection, workspace")
    if scope == "collection" and not collection_id:
        raise ValueError("collectionId is required for collection-scoped notes")
    if scope == "collection" and not can_access_collection_id(actor, collection_id):
        raise PermissionError("No access to selected collection")


def create_note(
    db: Session,
    actor: Actor,
    *,
    title: str,
    body: str,
    scope: str = "private",
    collection_id: str | None = None,
    tags: list[str] | None = None,
    anchors: list[dict] | None = None,
    metadata: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    normalized_scope = (scope or "private").lower()
    _validate_note_scope(actor, normalized_scope, collection_id)
    note_id = f"note-{uuid4().hex[:10]}"
    cleaned_title = _clean_text(title, 255) or "Untitled note"
    note = Note(
        id=note_id,
        title=cleaned_title,
        body=str(body or "").strip(),
        scope=normalized_scope,
        status="active",
        owner_id=actor.id,
        owner_name=actor.name,
        collection_id=collection_id if normalized_scope == "collection" else None,
        tags=[_clean_text(tag, 48) for tag in (tags or []) if _clean_text(tag, 48)],
        metadata_json=metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(note)
    db.add(
        NoteVersion(
            id=f"notev-{uuid4().hex[:10]}",
            note_id=note_id,
            version_no=1,
            title=cleaned_title,
            body=note.body,
            change_summary="Created note",
            created_by=actor.name,
            created_at=now,
        )
    )
    for anchor in anchors or []:
        db.add(
            NoteAnchor(
                id=f"notea-{uuid4().hex[:10]}",
                note_id=note_id,
                target_type=_clean_text(anchor.get("targetType") or "manual", 64),
                target_id=_clean_text(anchor.get("targetId"), 128) or None,
                source_id=_clean_text(anchor.get("sourceId"), 64) or None,
                chunk_id=_clean_text(anchor.get("chunkId"), 64) or None,
                artifact_id=_clean_text(anchor.get("artifactId"), 64) or None,
                page_id=_clean_text(anchor.get("pageId"), 64) or None,
                section_key=_clean_text(anchor.get("sectionKey"), 128) or None,
                review_item_id=_clean_text(anchor.get("reviewItemId"), 64) or None,
                ask_message_id=_clean_text(anchor.get("askMessageId"), 64) or None,
                citation_id=_clean_text(anchor.get("citationId"), 128) or None,
                snippet=str(anchor.get("snippet") or "").strip(),
                metadata_json=anchor.get("metadataJson") if isinstance(anchor.get("metadataJson"), dict) else {},
                created_at=now,
            )
        )
    db.commit()
    note = db.query(Note).filter(Note.id == note_id).first()
    return serialize_note(note)


def update_note(db: Session, note_id: str, actor: Actor, *, title: str | None = None, body: str | None = None, tags: list[str] | None = None) -> dict | None:
    note = db.query(Note).filter(Note.id == note_id, Note.status != "archived").first()
    if not note:
        return None
    if note.owner_id != actor.id and actor.role != "admin":
        raise PermissionError("Only the note owner or admin can edit this note")
    if title is not None:
        note.title = _clean_text(title, 255) or note.title
    if body is not None:
        note.body = str(body).strip()
    if tags is not None:
        note.tags = [_clean_text(tag, 48) for tag in tags if _clean_text(tag, 48)]
    note.updated_at = datetime.now(timezone.utc)
    version_no = len(note.versions) + 1
    db.add(
        NoteVersion(
            id=f"notev-{uuid4().hex[:10]}",
            note_id=note.id,
            version_no=version_no,
            title=note.title,
            body=note.body,
            change_summary="Updated note",
            created_by=actor.name,
            created_at=note.updated_at,
        )
    )
    db.commit()
    db.refresh(note)
    return serialize_note(note)


def archive_note(db: Session, note_id: str, actor: Actor) -> dict | None:
    note = db.query(Note).filter(Note.id == note_id, Note.status != "archived").first()
    if not note:
        return None
    if note.owner_id != actor.id and actor.role != "admin":
        raise PermissionError("Only the note owner or admin can archive this note")
    now = datetime.now(timezone.utc)
    note.status = "archived"
    note.archived_at = now
    note.updated_at = now
    db.commit()
    db.refresh(note)
    return serialize_note(note)


def restore_note(db: Session, note_id: str, actor: Actor) -> dict | None:
    note = db.query(Note).filter(Note.id == note_id, Note.status == "archived").first()
    if not note:
        return None
    if note.owner_id != actor.id and actor.role != "admin":
        raise PermissionError("Only the note owner or admin can restore this note")
    now = datetime.now(timezone.utc)
    note.status = "active"
    note.archived_at = None
    note.updated_at = now
    db.commit()
    db.refresh(note)
    return serialize_note(note)


def create_page_draft_from_note(db: Session, note_id: str, actor: Actor) -> dict | None:
    note = _visible_query(db, actor).filter(Note.id == note_id).first()
    if not note:
        return None
    source_ids = [anchor.source_id for anchor in note.anchors if anchor.source_id]
    content = f"# {note.title}\n\n{note.body}\n\n## Evidence Anchors\n"
    for anchor in note.anchors:
        content += f"\n- {anchor.target_type}: {anchor.snippet[:220]}"
    page = create_page_with_version(
        db,
        title=note.title,
        slug=f"{slugify(note.title)}-{uuid4().hex[:6]}",
        summary=note.body[:300],
        content_md=content,
        owner=actor.name,
        page_type="source_derived",
        status="draft",
        tags=list(set([*(note.tags or []), "from-note"])),
        key_facts=[note.body[:300]] if note.body else [],
        related_source_ids=list(dict.fromkeys(source_ids)),
        related_entity_ids=[],
        collection_id=note.collection_id,
    )
    note.metadata_json = {**(note.metadata_json or {}), "pageDraftId": page.id, "pageDraftSlug": page.slug}
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "pageId": page.id, "pageSlug": page.slug}


def create_review_item_from_note(db: Session, note_id: str, actor: Actor) -> dict | None:
    note = _visible_query(db, actor).filter(Note.id == note_id).first()
    if not note:
        return None
    page_anchor = next((anchor for anchor in note.anchors if anchor.page_id), None)
    if not page_anchor:
        raise ValueError("Note needs a page anchor before it can become a review item")
    now = datetime.now(timezone.utc)
    item = ReviewItem(
        id=f"rev-note-{uuid4().hex[:8]}",
        page_id=page_anchor.page_id,
        page_title=note.title,
        page_slug="",
        page_status="draft",
        issue_type="note_followup",
        severity="medium",
        old_content_md="",
        new_content_md=note.body,
        change_summary=f"Review note: {note.title}",
        confidence_score=0.7,
        created_at=now,
        updated_at=now,
        assigned_to=actor.name,
        previous_version=None,
        source_ids=[anchor.source_id for anchor in note.anchors if anchor.source_id],
        evidence_snippets=[{"noteId": note.id, "snippet": anchor.snippet, "targetType": anchor.target_type} for anchor in note.anchors],
    )
    db.add(item)
    note.metadata_json = {**(note.metadata_json or {}), "reviewItemId": item.id}
    note.updated_at = now
    db.commit()
    return {"success": True, "reviewItemId": item.id}
