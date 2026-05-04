from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_roles
from app.schemas.source import ClaimOut, EntityOut, ExtractionRunOut, KnowledgeUnitOut, PageOut, PaginatedResponse, SourceChunkOut, SourceOut
from app.services.job_queue import enqueue_source_job
from app.services.jobs import list_jobs_for_input
from app.services.sources import (
    MAX_UPLOAD_BYTES,
    archive_source,
    create_source_record,
    create_text_source_record,
    create_url_source_record,
    get_source_by_id,
    get_source_chunks,
    get_source_claims,
    get_source_extraction_runs,
    get_source_entities,
    get_source_knowledge_units,
    get_source_pages,
    get_connector_registry,
    list_sources as list_sources_service,
    refresh_url_source_record,
    restore_source,
)
from app.services.auth import Actor
from app.services.suggestions import (
    accept_suggestion,
    accept_pending_suggestions,
    change_suggestion_target,
    list_source_suggestions,
    reject_suggestion,
    reject_pending_suggestions,
    set_source_standalone,
)

router = APIRouter()


class SuggestionTargetPayload(BaseModel):
    targetId: str | None = None


class UrlIngestPayload(BaseModel):
    url: str
    title: str | None = None
    collectionId: str | None = None


class TextIngestPayload(BaseModel):
    title: str
    content: str
    sourceType: str = "txt"
    collectionId: str | None = None


class BulkSourcesPayload(BaseModel):
    sourceIds: list[str]
    action: str


def _source_response_with_job(source, job):
    return {
        "id": source.id,
        "title": source.title,
        "sourceType": source.source_type,
        "mimeType": source.mime_type,
        "filePath": source.file_path,
        "url": source.url,
        "uploadedAt": source.uploaded_at.isoformat(),
        "updatedAt": source.updated_at.isoformat(),
        "createdBy": source.created_by,
        "parseStatus": source.parse_status,
        "ingestStatus": source.ingest_status,
        "metadataJson": {**(source.metadata_json or {}), "jobId": job.id},
        "checksum": source.checksum,
        "trustLevel": source.trust_level,
        "fileSize": source.file_size,
        "description": source.description,
        "tags": source.tags or [],
        "collectionId": source.collection_id,
    }


@router.get("", response_model=PaginatedResponse[SourceOut])
async def list_sources(
    page: int = 1,
    pageSize: int = 20,
    status: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    collectionId: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_sources_service(db, page=page, page_size=pageSize, status=status, source_type=type, search=search, collection_id=collectionId)


@router.get("/connectors")
async def list_connectors():
    return get_connector_registry()


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: str, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/upload", response_model=SourceOut)
async def upload_source(
    file: UploadFile = File(...),
    collectionId: str | None = Form(None),
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_roles("editor", "reviewer", "admin")),
):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 25 MB limit")
    source, _ = create_source_record(
        db=db,
        filename=file.filename,
        mime_type=file.content_type or "",
        file_size=len(content),
        file_bytes=content,
        collection_id=collectionId,
        actor=actor.name,
    )
    job = enqueue_source_job(db, job_type="ingest", source_id=source.id, actor=actor.name, logs=["Upload received"])
    return _source_response_with_job(source, job)


@router.post("/url", response_model=SourceOut)
async def ingest_url_source(payload: UrlIngestPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    try:
        source, _ = create_url_source_record(
            db,
            url=payload.url,
            title=payload.title,
            collection_id=payload.collectionId,
            actor=actor.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = enqueue_source_job(db, job_type="ingest", source_id=source.id, actor=actor.name, logs=["URL received", f"Fetched {source.url}"])
    return _source_response_with_job(source, job)


@router.post("/text", response_model=SourceOut)
async def ingest_text_source(payload: TextIngestPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    try:
        source, _ = create_text_source_record(
            db,
            title=payload.title,
            content=payload.content,
            source_type=payload.sourceType,
            collection_id=payload.collectionId,
            actor=actor.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = enqueue_source_job(db, job_type="ingest", source_id=source.id, actor=actor.name, logs=["Text source received"])
    return _source_response_with_job(source, job)


@router.post("/bulk")
async def bulk_sources(payload: BulkSourcesPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    if payload.action not in {"archive", "restore"}:
        raise HTTPException(status_code=400, detail="Unsupported bulk source action")
    updated: list[str] = []
    skipped: list[str] = []
    for source_id in payload.sourceIds:
        result = archive_source(db, source_id, actor=actor.name) if payload.action == "archive" else restore_source(db, source_id, actor=actor.name)
        if result:
            updated.append(source_id)
        else:
            skipped.append(source_id)
    return {"success": True, "action": payload.action, "updatedCount": len(updated), "updatedIds": updated, "skippedIds": skipped}


@router.get("/{source_id}/chunks", response_model=PaginatedResponse[SourceChunkOut])
async def list_source_chunks(
    source_id: str,
    page: int = 1,
    pageSize: int = 20,
    db: Session = Depends(get_db),
):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_chunks(db, source_id=source_id, page=page, page_size=pageSize)


@router.get("/{source_id}/claims", response_model=list[ClaimOut])
async def list_source_claims(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_claims(db, source_id)


@router.get("/{source_id}/knowledge-units", response_model=list[KnowledgeUnitOut])
async def list_source_knowledge_units(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_knowledge_units(db, source_id)


@router.get("/{source_id}/extraction-runs", response_model=list[ExtractionRunOut])
async def list_source_extraction_runs(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_extraction_runs(db, source_id)


@router.get("/{source_id}/entities", response_model=list[EntityOut])
async def list_source_entities(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_entities(db, source_id)


@router.get("/{source_id}/affected-pages", response_model=list[PageOut])
async def list_affected_pages(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return get_source_pages(db, source_id)


@router.get("/{source_id}/suggestions")
async def list_suggestions(source_id: str, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return list_source_suggestions(db, source_id)


@router.get("/{source_id}/jobs")
async def list_source_jobs(source_id: str, limit: int = 20, db: Session = Depends(get_db)):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return list_jobs_for_input(db, source_id, limit=limit)


@router.post("/{source_id}/suggestions/accept-all")
async def accept_all_source_suggestions(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = accept_pending_suggestions(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/{source_id}/suggestions/reject-all")
async def reject_all_source_suggestions(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = reject_pending_suggestions(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/{source_id}/standalone")
async def mark_source_standalone(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = set_source_standalone(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/{source_id}/archive", response_model=SourceOut)
async def archive_source_route(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = archive_source(db, source_id, actor=actor.name)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/{source_id}/restore", response_model=SourceOut)
async def restore_source_route(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = restore_source(db, source_id, actor=actor.name)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/suggestions/{suggestion_id}/accept")
async def accept_source_suggestion(suggestion_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = accept_suggestion(db, suggestion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


@router.post("/suggestions/{suggestion_id}/reject")
async def reject_source_suggestion(suggestion_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = reject_suggestion(db, suggestion_id)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


@router.post("/suggestions/{suggestion_id}/target")
async def change_source_suggestion_target(suggestion_id: str, payload: SuggestionTargetPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = change_suggestion_target(db, suggestion_id, payload.targetId)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


@router.post("/{source_id}/rebuild")
async def rebuild_source(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    if not get_source_by_id(db, source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    job = enqueue_source_job(db, job_type="rebuild", source_id=source_id, actor=actor.name, logs=["Rebuild requested"])
    return {"jobId": job.id}


@router.post("/{source_id}/refresh")
async def refresh_source(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    source = refresh_url_source_record(db, source_id, actor=actor.name)
    if not source:
        raise HTTPException(status_code=404, detail="Refreshable URL source not found")
    job = enqueue_source_job(db, job_type="rebuild", source_id=source.id, actor=actor.name, logs=["URL refresh requested"])
    return {"jobId": job.id, "sourceId": source.id}
