from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_roles
from app.services.auth import Actor, actor_metadata
from app.services.review import (
    add_review_comment,
    approve_review_item,
    create_issue_page_from_review_item,
    get_review_item,
    list_review_items,
    merge_review_item,
    reject_review_item,
)

router = APIRouter()


class RejectPayload(BaseModel):
    reason: str


class MergePayload(BaseModel):
    targetPageId: str | None = None
    comment: str | None = None


class CommentPayload(BaseModel):
    comment: str


@router.get("")
async def get_review_queue(
    page: int = 1,
    pageSize: int = 20,
    severity: Optional[str] = None,
    issueType: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return list_review_items(db, page=page, page_size=pageSize, severity=severity, issue_type=issueType)


@router.get("/{item_id}")
async def get_review_item_route(item_id: str, db: Session = Depends(get_db)):
    item = get_review_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    return item


@router.post("/{item_id}/comments")
async def add_comment(item_id: str, payload: CommentPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    if not payload.comment.strip():
        raise HTTPException(status_code=400, detail="Comment is required")
    result = add_review_comment(db, item_id, payload.comment, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not result:
        raise HTTPException(status_code=404, detail="Review item not found")
    return result


@router.post("/{item_id}/approve")
async def approve_item(item_id: str, comment: Optional[str] = None, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reviewer", "admin"))):
    result = approve_review_item(db, item_id, comment=comment, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not result:
        raise HTTPException(status_code=404, detail="Review item not found")
    return result


@router.post("/{item_id}/reject")
async def reject_item(item_id: str, payload: RejectPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reviewer", "admin"))):
    result = reject_review_item(db, item_id, payload.reason, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not result:
        raise HTTPException(status_code=404, detail="Review item not found")
    return result


@router.post("/{item_id}/merge")
async def merge_item(item_id: str, payload: MergePayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("reviewer", "admin"))):
    result = merge_review_item(db, item_id, target_page_id=payload.targetPageId, comment=payload.comment, actor=actor.name, actor_metadata=actor_metadata(actor))
    if not result:
        raise HTTPException(status_code=404, detail="Review item or merge target not found")
    return result


@router.post("/{item_id}/create-issue-page")
async def create_issue_page(item_id: str, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    result = create_issue_page_from_review_item(db, item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Review item not found")
    return result
