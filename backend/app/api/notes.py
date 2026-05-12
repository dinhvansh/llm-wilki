from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_permission
from app.db.database import get_db
from app.services.auth import Actor
from app.services.notes import archive_note, create_note, create_page_draft_from_note, create_review_item_from_note, get_note, list_notes, restore_note, update_note

router = APIRouter()


class NoteAnchorIn(BaseModel):
    targetType: str = "manual"
    targetId: str | None = None
    sourceId: str | None = None
    chunkId: str | None = None
    artifactId: str | None = None
    pageId: str | None = None
    sectionKey: str | None = None
    reviewItemId: str | None = None
    askMessageId: str | None = None
    citationId: str | None = None
    snippet: str | None = None
    metadataJson: dict | None = None


class NoteCreateIn(BaseModel):
    title: str
    body: str = ""
    scope: str = "private"
    collectionId: str | None = None
    tags: list[str] = []
    anchors: list[NoteAnchorIn] = []
    metadataJson: dict | None = None


class NoteUpdateIn(BaseModel):
    title: str | None = None
    body: str | None = None
    tags: list[str] | None = None


@router.get("")
async def list_notes_route(
    sourceId: str | None = None,
    pageId: str | None = None,
    collectionId: str | None = None,
    search: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_permission("note:read")),
):
    return list_notes(db, actor, source_id=sourceId, page_id=pageId, collection_id=collectionId, search=search, limit=limit)


@router.get("/{note_id}")
async def get_note_route(note_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("note:read"))):
    note = get_note(db, note_id, actor)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("")
async def create_note_route(payload: NoteCreateIn, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("note:write"))):
    try:
        return create_note(
            db,
            actor,
            title=payload.title,
            body=payload.body,
            scope=payload.scope,
            collection_id=payload.collectionId,
            tags=payload.tags,
            anchors=[anchor.model_dump(by_alias=False) for anchor in payload.anchors],
            metadata=payload.metadataJson or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.patch("/{note_id}")
async def update_note_route(note_id: str, payload: NoteUpdateIn, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("note:write"))):
    try:
        note = update_note(db, note_id, actor, title=payload.title, body=payload.body, tags=payload.tags)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}")
async def archive_note_route(note_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("note:write"))):
    try:
        note = archive_note(db, note_id, actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/restore")
async def restore_note_route(note_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("note:write"))):
    try:
        note = restore_note(db, note_id, actor)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/{note_id}/page-draft")
async def create_page_draft_from_note_route(note_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    result = create_page_draft_from_note(db, note_id, actor)
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return result


@router.post("/{note_id}/review-item")
async def create_review_item_from_note_route(note_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("review:comment"))):
    try:
        result = create_review_item_from_note(db, note_id, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Note not found")
    return result
