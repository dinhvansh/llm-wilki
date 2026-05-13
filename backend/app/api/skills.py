from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.identity import require_permission
from app.db.database import get_db
from app.services.auth import Actor
from app.services.skills import (
    add_skill_review_comment,
    approve_skill_package,
    create_skill_package,
    get_skill_package,
    list_skill_packages,
    release_skill_package,
    submit_skill_for_review,
    test_skill_package,
    update_skill_package,
)


router = APIRouter()


class SkillCommentPayload(BaseModel):
    comment: str


class SkillReviewPayload(BaseModel):
    comment: str | None = None


class SkillUpsertPayload(BaseModel):
    id: str | None = None
    name: str
    version: str = "0.1.0"
    scope: str = "workspace"
    status: str = "draft"
    reviewStatus: str = "draft"
    summary: str = ""
    description: str = ""
    instructions: str = ""
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    entryPoints: list[str] = Field(default_factory=list)
    owner: str | None = None
    taskProfile: str = "ask_answer"
    metadataJson: dict = Field(default_factory=dict)
    changeComment: str | None = None


class SkillTestPayload(BaseModel):
    input: str = ""


@router.get("/skills")
async def list_skills(actor: Actor = Depends(require_permission("skill:read"))):
    return list_skill_packages()


@router.get("/skills/{package_id}")
async def get_skill(package_id: str, actor: Actor = Depends(require_permission("skill:read"))):
    package = get_skill_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills")
async def create_skill(payload: SkillUpsertPayload, actor: Actor = Depends(require_permission("skill:write"))):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Skill name is required")
    try:
        return create_skill_package(payload.model_dump(), actor=actor.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/skills/{package_id}")
async def update_skill(package_id: str, payload: SkillUpsertPayload, actor: Actor = Depends(require_permission("skill:write"))):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Skill name is required")
    package = update_skill_package(package_id, payload.model_dump(), actor=actor.name)
    if not package:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return package


@router.post("/skills/{package_id}/test")
async def test_skill(package_id: str, payload: SkillTestPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("skill:write"))):
    if not payload.input.strip():
        raise HTTPException(status_code=400, detail="Test input is required")
    result = test_skill_package(package_id, actor=actor.name, test_input=payload.input, db=db)
    if not result:
        raise HTTPException(status_code=404, detail="Skill package not found")
    return result


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
