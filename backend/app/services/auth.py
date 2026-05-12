from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import AuthSession, User
from app.services.permissions import get_collection_scope, permissions_for_role

ROLE_ORDER = {"reader": 0, "editor": 1, "reviewer": 2, "admin": 3}
DEV_ADMIN_EMAIL = "admin@local.test"
DEV_ADMIN_PASSWORD = "admin123"


@dataclass(frozen=True)
class Actor:
    id: str | None
    name: str
    role: str
    email: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    authenticated: bool = False
    permissions: tuple[str, ...] = ()
    collection_scope_mode: str = "all"
    accessible_collection_ids: tuple[str, ...] = ()
    collection_memberships: tuple[dict, ...] = ()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(actual, expected)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def serialize_user(db: Session, user: User) -> dict:
    scope = get_collection_scope(db, user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "departmentId": user.department_id,
        "departmentName": user.department.name if getattr(user, "department", None) else None,
        "permissions": sorted(permissions_for_role(user.role)),
        "scopeMode": scope.mode,
        "accessibleCollectionIds": scope.collection_ids,
        "collectionMemberships": scope.memberships,
    }


def ensure_dev_admin_user(db: Session) -> User:
    now = datetime.now(timezone.utc)
    user = db.query(User).filter(User.email == DEV_ADMIN_EMAIL).first()
    if user:
        return user
    user = User(
        id="user-dev-admin",
        email=DEV_ADMIN_EMAIL,
        name="Dev Admin",
        role="admin",
        password_hash=hash_password(DEV_ADMIN_PASSWORD),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.lower().strip(), User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User, ttl_hours: int = 24) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    session = AuthSession(
        id=f"session-{uuid4().hex[:12]}",
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        last_seen_at=now,
    )
    db.add(session)
    db.commit()
    return token, session


def get_user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    now = datetime.now(timezone.utc)
    session = (
        db.query(AuthSession)
        .join(User, User.id == AuthSession.user_id)
        .filter(
            AuthSession.token_hash == hash_token(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
            User.is_active.is_(True),
        )
        .first()
    )
    if not session:
        return None
    session.last_seen_at = now
    db.commit()
    return session.user


def revoke_token(db: Session, token: str) -> bool:
    session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token), AuthSession.revoked_at.is_(None)).first()
    if not session:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def actor_from_user(user: User) -> Actor:
    raise RuntimeError("actor_from_user now requires a database session; call build_actor instead")


def build_actor(db: Session, user: User) -> Actor:
    scope = get_collection_scope(db, user)
    permissions = tuple(sorted(permissions_for_role(user.role)))
    return Actor(
        id=user.id,
        name=user.name,
        role=user.role,
        email=user.email,
        department_id=user.department_id,
        department_name=user.department.name if getattr(user, "department", None) else None,
        authenticated=True,
        permissions=permissions,
        collection_scope_mode=scope.mode,
        accessible_collection_ids=tuple(scope.collection_ids),
        collection_memberships=tuple(scope.memberships),
    )


def actor_metadata(actor: Actor) -> dict:
    return {
        "actorUserId": actor.id,
        "actorName": actor.name,
        "actorRole": actor.role,
        "actorEmail": actor.email,
        "actorDepartmentId": actor.department_id,
        "actorDepartmentName": actor.department_name,
        "actorPermissions": list(actor.permissions),
        "actorScopeMode": actor.collection_scope_mode,
        "actorCollectionIds": list(actor.accessible_collection_ids),
        "actorCollectionCount": len(actor.accessible_collection_ids),
        "actorCollectionMemberships": [dict(item) for item in actor.collection_memberships],
    }


def has_role(actor: Actor, allowed_roles: set[str]) -> bool:
    if actor.role in allowed_roles:
        return True
    required_rank = min(ROLE_ORDER[role] for role in allowed_roles)
    return ROLE_ORDER.get(actor.role, -1) >= required_rank
