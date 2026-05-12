from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.auth import Actor, build_actor, get_user_for_token, has_role
from app.services.permissions import has_permission_set


def get_actor_name(x_user: str | None = Header(default=None, alias="X-User")) -> str:
    actor = " ".join((x_user or "").strip().split())
    if not actor:
        return "Current User"
    return actor[:128]


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_current_actor(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user: str | None = Header(default=None, alias="X-User"),
    db: Session = Depends(get_db),
) -> Actor:
    user = get_user_for_token(db, _bearer_token(authorization))
    if user:
        return build_actor(db, user)
    return Actor(id=None, name=get_actor_name(x_user), role="dev", authenticated=False)


def require_authenticated_actor(actor: Actor = Depends(get_current_actor)) -> Actor:
    if not actor.authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return actor


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(actor: Actor = Depends(require_authenticated_actor)) -> Actor:
        if not has_role(actor, allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return actor

    return dependency


def require_permission(permission: str):
    def dependency(actor: Actor = Depends(require_authenticated_actor)) -> Actor:
        if not has_permission_set(set(actor.permissions), permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return actor

    return dependency
