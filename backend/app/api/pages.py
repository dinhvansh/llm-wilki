from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_roles
from app.schemas.source import PageOut, PaginatedResponse
from app.services.auth import Actor, actor_metadata
from app.services.pages import (
    PageEditConflict,
    build_editor_insert_helpers,
    bulk_update_pages,
    compose_page,
    create_page_from_chunks,
    get_page_by_id,
    get_page_by_slug,
    get_page_audit_logs,
    get_page_diff,
    get_page_versions,
    list_entities,
    list_glossary_terms,
    list_pages as list_pages_service,
    list_timeline_events,
    publish_page,
    restore_page_version,
    unpublish_page,
    update_page_content,
)

router = APIRouter()


class ComposePayload(BaseModel):
    topic: str
    sourceIds: list[str] = []


class UpdatePagePayload(BaseModel):
    contentMd: str
    changeSummary: str | None = None
    expectedVersion: int | None = None


class RestoreVersionPayload(BaseModel):
    versionNo: int


class BulkPagesPayload(BaseModel):
    pageIds: list[str]
    action: str


class PageFromChunksPayload(BaseModel):
    title: str
    chunkIds: list[str]
    existingPageId: str | None = None


@router.get("", response_model=PaginatedResponse[PageOut])
async def list_pages(
    page: int = 1,
    pageSize: int = 20,
    status: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    collectionId: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_pages_service(db, page=page, page_size=pageSize, status=status, page_type=type, search=search, sort=sort, collection_id=collectionId)


@router.get("/entity-explorer")
async def entity_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    entityType: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_entities(db, page=page, page_size=pageSize, search=search, entity_type=entityType)


@router.get("/timeline-explorer")
async def timeline_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_timeline_events(db, page=page, page_size=pageSize, search=search)


@router.get("/glossary")
async def glossary_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_glossary_terms(db, page=page, page_size=pageSize, search=search)


@router.get("/{slug}", response_model=PageOut)
async def get_page(slug: str, db: Session = Depends(get_db)):
    page = get_page_by_slug(db, slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.get("/{page_id}/versions")
async def list_page_versions(page_id: str, db: Session = Depends(get_db)):
    return get_page_versions(db, page_id)


@router.get("/{page_id}/audit")
async def list_page_audit(page_id: str, limit: int = 50, db: Session = Depends(get_db)):
    if not get_page_by_id(db, page_id):
        raise HTTPException(status_code=404, detail="Page not found")
    return get_page_audit_logs(db, page_id, limit=limit)


@router.get("/{page_id}/diff")
async def get_page_diff_route(page_id: str, versionNo: int, db: Session = Depends(get_db)):
    diff = get_page_diff(db, page_id, versionNo)
    if not diff:
        raise HTTPException(status_code=404, detail="Page not found")
    return diff


@router.get("/{page_id}/insert-helpers")
async def get_insert_helpers(page_id: str, sourceId: Optional[str] = None, chunkId: Optional[str] = None, db: Session = Depends(get_db)):
    helpers = build_editor_insert_helpers(db, page_id, source_id=sourceId, chunk_id=chunkId)
    if not helpers:
        raise HTTPException(status_code=404, detail="Page not found")
    return helpers


@router.post("/compose", response_model=PageOut)
async def compose_page_route(payload: ComposePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    return compose_page(db, payload.topic, payload.sourceIds)


@router.post("/from-chunks", response_model=PageOut)
async def create_page_from_chunks_route(payload: PageFromChunksPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    page = create_page_from_chunks(db, title=payload.title, chunk_ids=payload.chunkIds, owner=actor.name, existing_page_id=payload.existingPageId)
    if not page:
        raise HTTPException(status_code=404, detail="Source chunks or target page not found")
    return page


@router.post("/bulk")
async def bulk_pages_route(payload: BulkPagesPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    if payload.action not in {"publish", "unpublish"}:
        raise HTTPException(status_code=400, detail="Unsupported bulk page action")
    return bulk_update_pages(db, payload.pageIds, payload.action, actor=actor.name, actor_metadata=actor_metadata(actor))


@router.post("/{page_id}/update", response_model=PageOut)
async def update_page_route(page_id: str, payload: UpdatePagePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    try:
        page = update_page_content(db, page_id, payload.contentMd, payload.changeSummary, author=actor.name, expected_version=payload.expectedVersion)
    except PageEditConflict as exc:
        raise HTTPException(status_code=409, detail={"message": "Page version conflict", "currentVersion": exc.current_version}) from exc
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/restore-version", response_model=PageOut)
async def restore_page_version_route(page_id: str, payload: RestoreVersionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    page = restore_page_version(db, page_id, payload.versionNo, author=actor.name)
    if not page:
        raise HTTPException(status_code=404, detail="Page or version not found")
    return page


@router.post("/{page_id}/publish", response_model=PageOut)
async def publish_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    page = publish_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/unpublish", response_model=PageOut)
async def unpublish_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    page = unpublish_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page
