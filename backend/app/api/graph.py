from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.runtime_config import load_runtime_snapshot
from app.services.graph import build_graph

router = APIRouter()


@router.get("/graph")
async def get_graph(
    nodeType: str = "all",
    status: str = "all",
    relationTypes: str | None = None,
    entityTypes: str | None = None,
    pageTypes: str | None = None,
    collectionId: str | None = None,
    focusId: str | None = None,
    localMode: bool = False,
    showOrphans: bool = False,
    showStale: bool = False,
    showConflicts: bool = False,
    showHubs: bool = False,
    limit: int | None = None,
    db: Session = Depends(get_db),
):
    runtime = load_runtime_snapshot(db)
    return build_graph(
        db,
        node_type=nodeType,
        status=status,
        relation_types=(relationTypes or "").split(","),
        entity_types=(entityTypes or "").split(","),
        page_types=(pageTypes or "").split(","),
        collection_id=collectionId,
        focus_id=focusId,
        local_mode=localMode,
        show_orphans=showOrphans,
        show_stale=showStale,
        show_conflicts=showConflicts,
        show_hubs=showHubs,
        limit=limit or runtime.graph_node_limit,
    )
