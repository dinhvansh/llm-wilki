from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.identity import require_authenticated_actor
from app.db.database import get_db
from app.schemas.auth import AuthResponse, LoginRequest, UserOut
from app.services.auth import Actor, authenticate_user, create_session, revoke_token, serialize_user

router = APIRouter()


def _token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token, _session = create_session(db, user)
    return {"token": token, "user": serialize_user(db, user)}


@router.get("/me", response_model=UserOut)
async def me(actor: Actor = Depends(require_authenticated_actor)):
    return {
        "id": actor.id or "",
        "email": actor.email or "",
        "name": actor.name,
        "role": actor.role,
        "departmentId": actor.department_id,
        "departmentName": actor.department_name,
        "permissions": list(actor.permissions),
        "scopeMode": actor.collection_scope_mode,
        "accessibleCollectionIds": list(actor.accessible_collection_ids),
        "collectionMemberships": list(actor.collection_memberships),
    }


@router.post("/logout")
async def logout(authorization: str | None = Header(default=None, alias="Authorization"), db: Session = Depends(get_db)):
    token = _token_from_header(authorization)
    if token:
        revoke_token(db, token)
    return {"success": True}
