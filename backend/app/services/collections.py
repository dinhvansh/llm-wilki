from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.ingest import slugify
from app.models import Collection, Page, Source
from app.services.audit import create_audit_log


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_collection(db: Session, collection: Collection) -> dict:
    return {
        "id": collection.id,
        "name": collection.name,
        "slug": collection.slug,
        "description": collection.description or "",
        "color": collection.color,
        "sourceCount": db.query(Source).filter(Source.collection_id == collection.id).count(),
        "pageCount": db.query(Page).filter(Page.collection_id == collection.id).count(),
        "createdAt": _iso(collection.created_at),
        "updatedAt": _iso(collection.updated_at),
    }


def list_collections(db: Session) -> list[dict]:
    collections = db.query(Collection).order_by(Collection.name.asc()).all()
    return [serialize_collection(db, collection) for collection in collections]


def get_collection_by_id(db: Session, collection_id: str) -> dict | None:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    return serialize_collection(db, collection) if collection else None


def create_collection(db: Session, name: str, description: str = "", color: str = "slate") -> dict:
    now = datetime.now(timezone.utc)
    base_slug = slugify(name) or f"collection-{uuid4().hex[:6]}"
    slug = base_slug
    suffix = 1
    while db.query(Collection).filter(Collection.slug == slug).first():
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    collection = Collection(
        id=f"col-{uuid4().hex[:8]}",
        name=name.strip(),
        slug=slug,
        description=description.strip(),
        color=color.strip() or "slate",
        created_at=now,
        updated_at=now,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return serialize_collection(db, collection)


def update_collection(db: Session, collection_id: str, name: str | None = None, description: str | None = None, color: str | None = None) -> dict | None:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        return None
    if name is not None and name.strip():
        collection.name = name.strip()
    if description is not None:
        collection.description = description.strip()
    if color is not None and color.strip():
        collection.color = color.strip()
    collection.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(collection)
    return serialize_collection(db, collection)


def delete_collection(db: Session, collection_id: str) -> bool:
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        return False
    db.query(Source).filter(Source.collection_id == collection_id).update({"collection_id": None})
    db.query(Page).filter(Page.collection_id == collection_id).update({"collection_id": None})
    db.delete(collection)
    db.commit()
    return True


def assign_source_collection(db: Session, source_id: str, collection_id: str | None, actor: str = "Current User") -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    source.collection_id = collection_id if collection_id else None
    source.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="assign_source_collection",
        object_type="source",
        object_id=source.id,
        actor=actor,
        summary=f"Assigned source `{source.title}` to collection `{source.collection_id or 'Standalone'}`",
        metadata={"collectionId": source.collection_id},
    )
    db.commit()
    return {"sourceId": source.id, "collectionId": source.collection_id}


def assign_page_collection(db: Session, page_id: str, collection_id: str | None, actor: str = "Current User") -> dict | None:
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        return None
    page.collection_id = collection_id if collection_id else None
    page.last_composed_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="assign_page_collection",
        object_type="page",
        object_id=page.id,
        actor=actor,
        summary=f"Assigned page `{page.title}` to collection `{page.collection_id or 'Standalone'}`",
        metadata={"collectionId": page.collection_id},
    )
    db.commit()
    return {"pageId": page.id, "collectionId": page.collection_id}
