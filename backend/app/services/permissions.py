from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import CollectionMembership, User

COLLECTION_ROLE_ORDER = {"viewer": 0, "contributor": 1, "editor": 2, "admin": 3}

ROLE_PERMISSION_MATRIX: dict[str, set[str]] = {
    "reader": {
        "collection:read",
        "source:read",
        "page:read",
        "graph:read",
        "ask:read",
        "skill:read",
        "dashboard:read",
        "glossary:read",
        "timeline:read",
        "diagram:read",
        "saved_view:read",
        "saved_view:write",
        "note:read",
    },
    "editor": {
        "collection:read",
        "collection:write",
        "source:read",
        "source:write",
        "page:read",
        "page:write",
        "graph:read",
        "ask:read",
        "skill:read",
        "skill:write",
        "dashboard:read",
        "glossary:read",
        "timeline:read",
        "diagram:read",
        "diagram:write",
        "review:read",
        "review:comment",
        "lint:read",
        "saved_view:read",
        "saved_view:write",
        "note:read",
        "note:write",
    },
    "reviewer": {
        "collection:read",
        "collection:write",
        "source:read",
        "source:write",
        "page:read",
        "page:write",
        "graph:read",
        "ask:read",
        "skill:read",
        "skill:write",
        "dashboard:read",
        "glossary:read",
        "timeline:read",
        "diagram:read",
        "diagram:write",
        "review:read",
        "review:comment",
        "review:approve",
        "lint:read",
        "admin:read",
        "settings:read",
        "saved_view:read",
        "saved_view:write",
        "note:read",
        "note:write",
    },
    "admin": {"*"},
}


@dataclass(frozen=True)
class CollectionScope:
    mode: str
    collection_ids: list[str]
    memberships: list[dict]


def permissions_for_role(role: str) -> set[str]:
    normalized = (role or "reader").lower()
    base = ROLE_PERMISSION_MATRIX.get(normalized, ROLE_PERMISSION_MATRIX["reader"])
    return set(base)


def has_permission_set(permissions: set[str], permission: str) -> bool:
    return "*" in permissions or permission in permissions


def get_collection_scope(db: Session, user: User | None) -> CollectionScope:
    if user is None or user.role == "admin":
        return CollectionScope(mode="all", collection_ids=[], memberships=[])
    memberships = (
        db.query(CollectionMembership)
        .filter(CollectionMembership.user_id == user.id)
        .order_by(CollectionMembership.created_at.asc())
        .all()
    )
    if not memberships:
        return CollectionScope(mode="all", collection_ids=[], memberships=[])
    serialized = [
        {
            "collectionId": membership.collection_id,
            "role": membership.role,
        }
        for membership in memberships
    ]
    return CollectionScope(
        mode="restricted",
        collection_ids=[membership.collection_id for membership in memberships],
        memberships=serialized,
    )


def collection_role_at_least(member_role: str | None, required_role: str) -> bool:
    member_level = COLLECTION_ROLE_ORDER.get((member_role or "").lower(), -1)
    required_level = COLLECTION_ROLE_ORDER.get(required_role.lower(), 99)
    return member_level >= required_level


def membership_role_for_collection(scope: CollectionScope, collection_id: str | None) -> str | None:
    if not collection_id:
        return None
    for membership in scope.memberships:
        if membership["collectionId"] == collection_id:
            return str(membership["role"])
    return None


def apply_collection_scope_filter(query, model, actor, collection_field_name: str = "collection_id"):
    if actor.role == "admin" or actor.collection_scope_mode != "restricted":
        return query
    collection_ids = list(actor.accessible_collection_ids)
    if not collection_ids:
        return query.filter(getattr(model, collection_field_name).is_(None))
    return query.filter(
        or_(
            getattr(model, collection_field_name).is_(None),
            getattr(model, collection_field_name).in_(collection_ids),
        )
    )


def can_access_collection_id(actor, collection_id: str | None) -> bool:
    if actor.role == "admin" or actor.collection_scope_mode != "restricted":
        return True
    if not collection_id:
        return True
    return collection_id in set(actor.accessible_collection_ids)
