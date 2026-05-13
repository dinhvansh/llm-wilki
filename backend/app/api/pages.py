import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.ingest import ensure_upload_dir
from app.db.database import get_db
from app.core.identity import require_authenticated_actor, require_permission, require_roles
from app.schemas.source import PageOut, PaginatedResponse
from app.services.auth import Actor, actor_metadata
from app.services.pages import (
    archive_page,
    archive_entity,
    PageEditConflict,
    build_editor_insert_helpers,
    bulk_update_pages,
    compose_page,
    create_page_from_chunks,
    get_entity_detail,
    get_page_by_id,
    get_page_by_slug,
    get_page_audit_logs,
    get_page_diff,
    get_page_versions,
    list_entities,
    list_glossary_terms,
    list_pages as list_pages_service,
    list_timeline_events,
    merge_entity_into,
    publish_page,
    restore_page,
    restore_entity,
    restore_page_version,
    set_entity_verification,
    unpublish_page,
    update_entity,
    update_page_content,
)

router = APIRouter()
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")
ALLOWED_PAGE_ASSET_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ComposePayload(BaseModel):
    topic: str
    sourceIds: list[str] = []
    contentMd: str | None = None
    contentJson: list[dict] | None = None
    collectionId: str | None = None
    pageType: str = "summary"


class UpdatePagePayload(BaseModel):
    contentMd: str | None = None
    contentJson: list[dict] | None = None
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


class UpdateEntityPayload(BaseModel):
    name: str
    entityType: str
    description: str = ""
    aliases: list[str] = []


class VerifyEntityPayload(BaseModel):
    verificationStatus: str


class MergeEntityPayload(BaseModel):
    targetEntityId: str


def _safe_page_asset_name(filename: str | None, content_type: str) -> str:
    extension = Path(filename or "").suffix.lower() or ALLOWED_PAGE_ASSET_MIME_TYPES.get(content_type, ".png")
    stem = Path(filename or "clipboard-image").stem
    normalized_stem = SAFE_FILENAME_RE.sub("-", stem).strip("-._") or "clipboard-image"
    return f"{normalized_stem}{extension}"


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
    actor: Actor = Depends(require_authenticated_actor),
):
    return list_pages_service(db, page=page, page_size=pageSize, status=status, page_type=type, search=search, sort=sort, collection_id=collectionId, actor=actor)


@router.get("/entity-explorer")
async def entity_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    entityType: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_authenticated_actor),
):
    return list_entities(db, page=page, page_size=pageSize, search=search, entity_type=entityType)


@router.get("/entity-explorer/{entity_id}")
async def get_entity_route(entity_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    entity = get_entity_detail(db, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entity-explorer/{entity_id}/update")
async def update_entity_route(entity_id: str, payload: UpdateEntityPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    try:
        entity = update_entity(
            db,
            entity_id,
            name=payload.name,
            entity_type=payload.entityType,
            description=payload.description,
            aliases=payload.aliases,
            actor=actor.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entity-explorer/{entity_id}/verify")
async def verify_entity_route(entity_id: str, payload: VerifyEntityPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    entity = set_entity_verification(db, entity_id, payload.verificationStatus, actor=actor.name)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entity-explorer/{entity_id}/archive")
async def archive_entity_route(entity_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    entity = archive_entity(db, entity_id, actor=actor.name)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entity-explorer/{entity_id}/restore")
async def restore_entity_route(entity_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    entity = restore_entity(db, entity_id, actor=actor.name)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entity-explorer/{entity_id}/merge")
async def merge_entity_route(entity_id: str, payload: MergeEntityPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    entity = merge_entity_into(db, entity_id, payload.targetEntityId, actor=actor.name)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity or merge target not found")
    return entity


@router.get("/timeline-explorer")
async def timeline_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_authenticated_actor),
):
    return list_timeline_events(db, page=page, page_size=pageSize, search=search)


@router.get("/glossary")
async def glossary_explorer(
    page: int = 1,
    pageSize: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_authenticated_actor),
):
    return list_glossary_terms(db, page=page, page_size=pageSize, search=search)


@router.get("/{slug}", response_model=PageOut)
async def get_page(slug: str, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    page = get_page_by_slug(db, slug, actor=actor)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.get("/{page_id}/versions")
async def list_page_versions(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    if not get_page_by_id(db, page_id, actor=actor):
        raise HTTPException(status_code=404, detail="Page not found")
    return get_page_versions(db, page_id)


@router.get("/{page_id}/audit")
async def list_page_audit(page_id: str, limit: int = 50, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    if not get_page_by_id(db, page_id, actor=actor):
        raise HTTPException(status_code=404, detail="Page not found")
    return get_page_audit_logs(db, page_id, limit=limit)


@router.get("/{page_id}/diff")
async def get_page_diff_route(page_id: str, versionNo: int, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    if not get_page_by_id(db, page_id, actor=actor):
        raise HTTPException(status_code=404, detail="Page not found")
    diff = get_page_diff(db, page_id, versionNo)
    if not diff:
        raise HTTPException(status_code=404, detail="Page not found")
    return diff


@router.get("/{page_id}/insert-helpers")
async def get_insert_helpers(page_id: str, sourceId: Optional[str] = None, chunkId: Optional[str] = None, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    if not get_page_by_id(db, page_id, actor=actor):
        raise HTTPException(status_code=404, detail="Page not found")
    helpers = build_editor_insert_helpers(db, page_id, source_id=sourceId, chunk_id=chunkId)
    if not helpers:
        raise HTTPException(status_code=404, detail="Page not found")
    return helpers


@router.post("/compose", response_model=PageOut)
async def compose_page_route(payload: ComposePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    return compose_page(
        db,
        payload.topic,
        payload.sourceIds,
        content_md=payload.contentMd,
        content_json=payload.contentJson,
        collection_id=payload.collectionId,
        page_type=payload.pageType,
    )


@router.post("/from-chunks", response_model=PageOut)
async def create_page_from_chunks_route(payload: PageFromChunksPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = create_page_from_chunks(db, title=payload.title, chunk_ids=payload.chunkIds, owner=actor.name, existing_page_id=payload.existingPageId)
    if not page:
        raise HTTPException(status_code=404, detail="Source chunks or target page not found")
    return page


@router.post("/assets")
async def upload_page_asset(file: UploadFile = File(...), actor: Actor = Depends(require_permission("page:write"))):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_PAGE_ASSET_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported page asset type")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    assets_dir = ensure_upload_dir() / "page-assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    original_name = _safe_page_asset_name(file.filename, content_type)
    stored_name = f"{uuid4().hex[:12]}-{original_name}"
    target = assets_dir / stored_name
    target.write_bytes(file_bytes)

    return {
        "filename": original_name,
        "contentType": content_type,
        "url": f"/uploads/page-assets/{stored_name}",
        "size": len(file_bytes),
    }


@router.post("/bulk")
async def bulk_pages_route(payload: BulkPagesPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    if payload.action not in {"publish", "unpublish", "archive", "restore"}:
        raise HTTPException(status_code=400, detail="Unsupported bulk page action")
    return bulk_update_pages(db, payload.pageIds, payload.action, actor=actor.name, actor_metadata=actor_metadata(actor))


@router.post("/{page_id}/update", response_model=PageOut)
async def update_page_route(page_id: str, payload: UpdatePagePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    try:
        page = update_page_content(
            db,
            page_id,
            payload.contentMd,
            payload.changeSummary,
            author=actor.name,
            expected_version=payload.expectedVersion,
            content_json=payload.contentJson,
        )
    except PageEditConflict as exc:
        raise HTTPException(status_code=409, detail={"message": "Page version conflict", "currentVersion": exc.current_version}) from exc
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/restore-version", response_model=PageOut)
async def restore_page_version_route(page_id: str, payload: RestoreVersionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = restore_page_version(db, page_id, payload.versionNo, author=actor.name)
    if not page:
        raise HTTPException(status_code=404, detail="Page or version not found")
    return page


@router.post("/{page_id}/publish", response_model=PageOut)
async def publish_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = publish_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/unpublish", response_model=PageOut)
async def unpublish_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = unpublish_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/archive", response_model=PageOut)
async def archive_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = archive_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/{page_id}/restore", response_model=PageOut)
async def restore_page_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("page:write"))):
    page = restore_page(db, page_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page
