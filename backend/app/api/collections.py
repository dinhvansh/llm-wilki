from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_authenticated_actor, require_permission, require_roles
from app.services.auth import Actor
from app.schemas.source import CollectionOut
from app.services.collections import (
    assign_page_collection,
    assign_source_collection,
    create_collection,
    delete_collection,
    get_collection_by_id,
    list_collections,
    set_collection_memberships,
    update_collection,
)

router = APIRouter()


class CollectionPayload(BaseModel):
    name: str
    description: str = ""
    color: str = "slate"


class AssignCollectionPayload(BaseModel):
    collectionId: str | None = None


class CollectionMembershipPayload(BaseModel):
    userId: str
    role: str = "viewer"


class CollectionMembershipUpdatePayload(BaseModel):
    memberships: list[CollectionMembershipPayload]


@router.get("", response_model=list[CollectionOut])
async def list_collection_route(db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    return list_collections(db, actor=actor)


@router.get("/{collection_id}", response_model=CollectionOut)
async def get_collection_route(collection_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_authenticated_actor)):
    collection = get_collection_by_id(db, collection_id, actor=actor)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("", response_model=CollectionOut)
async def create_collection_route(payload: CollectionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("collection:write"))):
    return create_collection(db, payload.name, payload.description, payload.color)


@router.patch("/{collection_id}", response_model=CollectionOut)
async def update_collection_route(collection_id: str, payload: CollectionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("collection:write"))):
    collection = update_collection(db, collection_id, payload.name, payload.description, payload.color)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.delete("/{collection_id}")
async def delete_collection_route(collection_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("admin"))):
    if not delete_collection(db, collection_id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"success": True}


@router.post("/sources/{source_id}/assign")
async def assign_source_route(source_id: str, payload: AssignCollectionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("collection:write"))):
    result = assign_source_collection(db, source_id, payload.collectionId, actor=actor.name)
    if not result:
        raise HTTPException(status_code=404, detail="Source not found")
    return result


@router.post("/pages/{page_id}/assign")
async def assign_page_route(page_id: str, payload: AssignCollectionPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("collection:write"))):
    result = assign_page_collection(db, page_id, payload.collectionId, actor=actor.name)
    if not result:
        raise HTTPException(status_code=404, detail="Page not found")
    return result


@router.put("/{collection_id}/memberships")
async def update_collection_memberships(
    collection_id: str,
    payload: CollectionMembershipUpdatePayload,
    db: Session = Depends(get_db),
    actor: Actor = Depends(require_permission("collection:write")),
):
    if actor.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can manage collection memberships")
    result = set_collection_memberships(
        db,
        collection_id,
        [membership.model_dump() for membership in payload.memberships],
        actor=actor.name,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Collection not found")
    return result
