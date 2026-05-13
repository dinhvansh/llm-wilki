from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_permission
from app.db.database import get_db
from app.schemas.diagram import DiagramOut, DiagramVersionOut, PaginatedResponse
from app.services.auth import Actor, actor_metadata
from app.services.diagrams import (
    approve_diagram_review,
    assess_page_bpm_fit,
    assess_source_bpm_fit,
    DiagramEditConflict,
    create_diagram,
    generate_diagram_from_page,
    generate_diagram_from_source,
    get_diagram_audit_logs,
    get_diagram_by_id,
    get_diagram_by_slug,
    get_diagram_versions,
    list_diagrams,
    publish_diagram,
    request_diagram_changes,
    submit_diagram_for_review,
    unpublish_diagram,
    update_diagram,
)

router = APIRouter()


class CreateDiagramPayload(BaseModel):
    title: str
    objective: str = ""
    owner: str | None = None
    collectionId: str | None = None
    actorLanes: list[str] = []
    sourcePageIds: list[str] = []
    sourceIds: list[str] = []
    entryPoints: list[str] = []
    exitPoints: list[str] = []
    relatedDiagramIds: list[str] = []
    flowDocument: dict = {}


class UpdateDiagramPayload(CreateDiagramPayload):
    changeSummary: str | None = None
    expectedVersion: int | None = None


class GenerateDiagramPayload(BaseModel):
    title: str | None = None
    objective: str | None = None


class FlowImportPayload(BaseModel):
    title: str
    objective: str = ""
    source: str
    format: str = "mermaid"


class ReviewPayload(BaseModel):
    comment: str | None = None


@router.get("", response_model=PaginatedResponse[DiagramOut])
async def list_diagrams_route(
    page: int = 1,
    pageSize: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    collectionId: Optional[str] = None,
    pageId: Optional[str] = None,
    sourceId: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_permission("diagram:read")),
):
    return list_diagrams(db, page=page, page_size=pageSize, status=status, search=search, collection_id=collectionId, page_id=pageId, source_id=sourceId)


@router.get("/assess-page/{page_id}")
async def assess_page_bpm_route(page_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    result = assess_page_bpm_fit(db, page_id)
    if not result:
        raise HTTPException(status_code=404, detail="Page not found")
    return result


@router.get("/assess-source/{source_id}")
async def assess_source_bpm_route(source_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    result = assess_source_bpm_fit(db, source_id)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.get("/{slug}", response_model=DiagramOut)
async def get_diagram_route(slug: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    diagram = get_diagram_by_slug(db, slug)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.get("/{diagram_id}/versions", response_model=list[DiagramVersionOut])
async def list_diagram_versions_route(diagram_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    if not get_diagram_by_id(db, diagram_id):
        raise HTTPException(status_code=404, detail="Diagram not found")
    return get_diagram_versions(db, diagram_id)


@router.get("/{diagram_id}/audit")
async def list_diagram_audit_route(diagram_id: str, limit: int = 50, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    if not get_diagram_by_id(db, diagram_id):
        raise HTTPException(status_code=404, detail="Diagram not found")
    return get_diagram_audit_logs(db, diagram_id, limit=limit)


@router.post("", response_model=DiagramOut)
async def create_diagram_route(payload: CreateDiagramPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    return create_diagram(
        db,
        title=payload.title,
        objective=payload.objective,
        owner=(payload.owner or actor.name).strip() or actor.name,
        collection_id=payload.collectionId,
        actor_lanes=payload.actorLanes,
        source_page_ids=payload.sourcePageIds,
        source_ids=payload.sourceIds,
        entry_points=payload.entryPoints,
        exit_points=payload.exitPoints,
        related_diagram_ids=payload.relatedDiagramIds,
        flow_document=payload.flowDocument,
    )


@router.post("/from-page/{page_id}", response_model=DiagramOut)
async def generate_diagram_from_page_route(
    page_id: str,
    payload: GenerateDiagramPayload | None = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_permission("diagram:write")),
):
    diagram = generate_diagram_from_page(db, page_id, actor=actor.name)
    if not diagram:
        raise HTTPException(status_code=404, detail="Page not found")
    if payload and (
        (payload.title and payload.title != diagram["title"])
        or (payload.objective and payload.objective != diagram["objective"])
    ):
        diagram = update_diagram(
            db,
            diagram["id"],
            title=payload.title or diagram["title"],
            objective=payload.objective or diagram["objective"],
            owner=diagram["owner"],
            actor=actor.name,
            collection_id=diagram["collectionId"],
            actor_lanes=diagram["actorLanes"],
            source_page_ids=diagram["sourcePageIds"],
            source_ids=diagram["sourceIds"],
            entry_points=diagram["entryPoints"],
            exit_points=diagram["exitPoints"],
            related_diagram_ids=diagram["relatedDiagramIds"],
            flow_document=diagram["flowDocument"],
            change_summary="Customize generated BPM draft",
            expected_version=diagram["currentVersion"],
        )
    return diagram


@router.post("/from-source/{source_id}", response_model=DiagramOut)
async def generate_diagram_from_source_route(
    source_id: str,
    payload: GenerateDiagramPayload | None = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_permission("diagram:write")),
):
    diagram = generate_diagram_from_source(db, source_id, actor=actor.name)
    if not diagram:
        raise HTTPException(status_code=404, detail="Source not found")
    if payload and (
        (payload.title and payload.title != diagram["title"])
        or (payload.objective and payload.objective != diagram["objective"])
    ):
        diagram = update_diagram(
            db,
            diagram["id"],
            title=payload.title or diagram["title"],
            objective=payload.objective or diagram["objective"],
            owner=diagram["owner"],
            actor=actor.name,
            collection_id=diagram["collectionId"],
            actor_lanes=diagram["actorLanes"],
            source_page_ids=diagram["sourcePageIds"],
            source_ids=diagram["sourceIds"],
            entry_points=diagram["entryPoints"],
            exit_points=diagram["exitPoints"],
            related_diagram_ids=diagram["relatedDiagramIds"],
            flow_document=diagram["flowDocument"],
            change_summary="Customize generated BPM draft",
            expected_version=diagram["currentVersion"],
        )
    return diagram


@router.post("/{diagram_id}/update", response_model=DiagramOut)
async def update_diagram_route(diagram_id: str, payload: UpdateDiagramPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    try:
        diagram = update_diagram(
            db,
            diagram_id,
            title=payload.title,
            objective=payload.objective,
            owner=(payload.owner or actor.name).strip() or actor.name,
            actor=actor.name,
            collection_id=payload.collectionId,
            actor_lanes=payload.actorLanes,
            source_page_ids=payload.sourcePageIds,
            source_ids=payload.sourceIds,
            entry_points=payload.entryPoints,
            exit_points=payload.exitPoints,
            related_diagram_ids=payload.relatedDiagramIds,
            flow_document=payload.flowDocument,
            change_summary=payload.changeSummary,
            expected_version=payload.expectedVersion,
        )
    except DiagramEditConflict as exc:
        raise HTTPException(status_code=409, detail={"message": "Diagram version conflict", "currentVersion": exc.current_version}) from exc
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.post("/import", response_model=DiagramOut)
async def import_diagram_route(payload: FlowImportPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    from app.services.diagrams import create_diagram_from_import

    diagram = create_diagram_from_import(
        db,
        title=payload.title,
        objective=payload.objective,
        source=payload.source,
        source_format=payload.format,
        actor=actor.name,
    )
    return diagram


@router.post("/{diagram_id}/validate")
async def validate_diagram_route(diagram_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    from app.services.diagrams import validate_diagram_flow

    result = validate_diagram_flow(db, diagram_id)
    if not result:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return result


@router.get("/{diagram_id}/export/{format}")
async def export_diagram_route(diagram_id: str, format: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:read"))):
    from app.services.diagrams import export_diagram_flow

    result = export_diagram_flow(db, diagram_id, format=format)
    if not result:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return result


@router.post("/{diagram_id}/publish", response_model=DiagramOut)
async def publish_diagram_route(diagram_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    diagram = publish_diagram(db, diagram_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.post("/{diagram_id}/submit-review", response_model=DiagramOut)
async def submit_diagram_review_route(diagram_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    diagram = submit_diagram_for_review(db, diagram_id, actor=actor.name)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.post("/{diagram_id}/approve-review", response_model=DiagramOut)
async def approve_diagram_review_route(diagram_id: str, payload: ReviewPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("review:approve"))):
    diagram = approve_diagram_review(db, diagram_id, actor=actor.name, comment=payload.comment)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.post("/{diagram_id}/request-changes", response_model=DiagramOut)
async def request_diagram_changes_route(diagram_id: str, payload: ReviewPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("review:approve"))):
    diagram = request_diagram_changes(db, diagram_id, actor=actor.name, comment=payload.comment)
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram


@router.post("/{diagram_id}/unpublish", response_model=DiagramOut)
async def unpublish_diagram_route(diagram_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("diagram:write"))):
    diagram = unpublish_diagram(db, diagram_id, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram
