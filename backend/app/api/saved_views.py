from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.identity import require_roles
from app.db.database import get_db
from app.models import SavedView
from app.services.auth import Actor

router = APIRouter()


class SavedViewPayload(BaseModel):
    name: str
    viewType: str
    filters: dict = {}


def _serialize(view: SavedView) -> dict:
    return {
        "id": view.id,
        "owner": view.owner,
        "name": view.name,
        "viewType": view.view_type,
        "filters": view.filters_json or {},
        "createdAt": view.created_at.isoformat(),
        "updatedAt": view.updated_at.isoformat(),
    }


@router.get("")
async def list_saved_views(viewType: str | None = None, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reader", "editor", "reviewer", "admin"))):
    query = db.query(SavedView).filter(SavedView.owner == actor.name)
    if viewType:
        query = query.filter(SavedView.view_type == viewType)
    rows = query.order_by(SavedView.updated_at.desc()).all()
    return [_serialize(row) for row in rows]


@router.post("")
async def create_saved_view(payload: SavedViewPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reader", "editor", "reviewer", "admin"))):
    now = datetime.now(timezone.utc)
    view = SavedView(
        id=f"sv-{uuid4().hex[:12]}",
        owner=actor.name,
        name=payload.name.strip()[:128],
        view_type=payload.viewType.strip()[:64],
        filters_json=payload.filters or {},
        created_at=now,
        updated_at=now,
    )
    if not view.name or not view.view_type:
        raise HTTPException(status_code=400, detail="Saved view name and type are required")
    db.add(view)
    db.commit()
    return _serialize(view)


@router.put("/{view_id}")
async def update_saved_view(view_id: str, payload: SavedViewPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reader", "editor", "reviewer", "admin"))):
    view = db.query(SavedView).filter(SavedView.id == view_id, SavedView.owner == actor.name).first()
    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")
    view.name = payload.name.strip()[:128]
    view.view_type = payload.viewType.strip()[:64]
    view.filters_json = payload.filters or {}
    view.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _serialize(view)


@router.delete("/{view_id}")
async def delete_saved_view(view_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reader", "editor", "reviewer", "admin"))):
    view = db.query(SavedView).filter(SavedView.id == view_id, SavedView.owner == actor.name).first()
    if not view:
        raise HTTPException(status_code=404, detail="Saved view not found")
    db.delete(view)
    db.commit()
    return {"success": True}
