from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.identity import require_permission
from app.services.auth import Actor
from app.services.skills import (
    add_skill_review_comment,
    approve_skill_package,
    get_skill_package,
    list_skill_packages,
    release_skill_package,
    submit_skill_for_review,
)


router = APIRouter()


class SkillCommentPayload(BaseModel):
    comment: str


class SkillReviewPayload(BaseModel):
    comment: str | None = None


@router.get("/skills")
async def list_skills(actor: Actor = Depends(require_permission("skill:read"))):
    return list_skill_packages()


@router.get("/skills/{package_id}")
async def get_skill(package_id: str, actor: Actor = Depends(require_permission("skill:read"))):
    package = get_skill_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills/{package_id}/comments")
async def add_skill_comment(package_id: str, payload: SkillCommentPayload, actor: Actor = Depends(require_permission("skill:write"))):
    if not payload.comment.strip():
        raise HTTPException(status_code=400, detail="Comment is required")
    package = add_skill_review_comment(package_id, actor=actor.name, comment=payload.comment)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills/{package_id}/submit-review")
async def submit_skill_review(package_id: str, payload: SkillReviewPayload, actor: Actor = Depends(require_permission("skill:write"))):
    package = submit_skill_for_review(package_id, actor=actor.name, comment=payload.comment)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills/{package_id}/approve")
async def approve_skill(package_id: str, payload: SkillReviewPayload, actor: Actor = Depends(require_permission("skill:write"))):
    package = approve_skill_package(package_id, actor=actor.name, comment=payload.comment)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills/{package_id}/release")
async def release_skill(package_id: str, payload: SkillReviewPayload, actor: Actor = Depends(require_permission("skill:write"))):
    package = release_skill_package(package_id, actor=actor.name, comment=payload.comment)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package
