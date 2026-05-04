from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_roles
from app.core.runtime_config import load_runtime_snapshot
from app.services.auth import Actor
from app.services.lint import execute_lint_quick_fix, run_lint

router = APIRouter()


class QuickFixPayload(BaseModel):
    action: str
    payload: dict = {}


@router.get("/lint")
async def get_lint_results(
    page: int = 1,
    pageSize: int = 50,
    severity: Optional[str] = None,
    ruleId: Optional[str] = None,
    search: Optional[str] = None,
    pageType: Optional[str] = None,
    collectionId: Optional[str] = None,
    db: Session = Depends(get_db),
):
    runtime = load_runtime_snapshot(db)
    return run_lint(
        db,
        page=page,
        page_size=pageSize,
        severity=severity,
        rule_id=ruleId,
        search=search,
        page_type=pageType,
        collection_id=collectionId,
        max_pages=runtime.lint_page_limit,
    )


@router.post("/lint/actions")
async def run_lint_action(payload: QuickFixPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_roles("editor", "reviewer", "admin"))):
    return execute_lint_quick_fix(db, payload.action, payload.payload, actor=actor.name)
