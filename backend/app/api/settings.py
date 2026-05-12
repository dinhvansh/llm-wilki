from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.identity import require_permission
from app.services.auth import Actor
from app.schemas.settings import SettingsPayload, SettingsResponse, TestConnectionPayload, TestConnectionResponse
from app.services.settings import serialize_runtime_settings, test_runtime_connection, update_runtime_settings

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db), actor: Actor = Depends(require_permission("settings:read"))):
    return serialize_runtime_settings(db)


@router.put("/settings", response_model=SettingsResponse)
async def save_settings(payload: SettingsPayload, db: Session = Depends(get_db), actor: Actor = Depends(require_permission("settings:write"))):
    return update_runtime_settings(db, payload.model_dump(), actor_name=actor.name)


@router.post("/settings/test", response_model=TestConnectionResponse)
async def test_settings_connection(payload: TestConnectionPayload, actor: Actor = Depends(require_permission("settings:write"))):
    return test_runtime_connection(payload.model_dump())
