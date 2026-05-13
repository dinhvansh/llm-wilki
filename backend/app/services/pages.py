from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.ingest import SENTENCE_RE, build_tags, summarize_text
from app.models import Claim, GlossaryTerm, Page, PageClaimLink, PageEntityLink, PageLink, PageSourceLink, PageVersion, Source, SourceChunk, TimelineEvent
from app.services.audit import create_audit_log, list_audit_logs
from app.services.page_blocks import markdown_to_blocks, normalize_page_document
from app.services.permissions import apply_collection_scope_filter, can_access_collection_id


class PageEditConflict(Exception):
    def __init__(self, current_version: int):
        super().__init__("Page version conflict")
        self.current_version = current_version


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _lightweight_summary(text: str, fallback_title: str) -> str:
    cleaned = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith(">")
    )
    sentences = [sentence.strip() for sentence in SENTENCE_RE.split(cleaned) if sentence.strip()]
    summary = " ".join(sentences[:2]).strip() if sentences else ""
    if summary:
        return summary[:320]
    return f"Draft page for {fallback_title.strip()}".strip()


def _page_source_map(db: Session, page_ids: list[str]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    if not page_ids:
        return mapping
    for page_id, source_id in db.query(PageSourceLink.page_id, PageSourceLink.source_id).filter(PageSourceLink.page_id.in_(page_ids)).all():
        mapping.setdefault(page_id, []).append(source_id)
    return mapping


def _page_timeline_map(db: Session, page_ids: list[str]) -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {}
    if not page_ids:
        return mapping
    records = db.query(TimelineEvent).filter(TimelineEvent.page_id.in_(page_ids)).order_by(TimelineEvent.sort_key.asc()).all()
    for record in records:
        mapping.setdefault(record.page_id or "", []).append(
            {
                "id": record.id,
                "eventDate": record.event_date,
                "sortKey": record.sort_key,
                "title": record.title,
                "description": record.description,
                "precision": record.precision,
                "entityIds": record.entity_ids or [],
                "sourceId": record.source_id,
                "pageId": record.page_id,
            }
        )
    return mapping


def _page_glossary_map(db: Session, page_ids: list[str]) -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {}
    if not page_ids:
        return mapping
    records = db.query(GlossaryTerm).filter(GlossaryTerm.page_id.in_(page_ids)).order_by(GlossaryTerm.term.asc()).all()
    for record in records:
        mapping.setdefault(record.page_id or "", []).append(
            {
                "id": record.id,
                "term": record.term,
                "normalizedTerm": record.normalized_term,
                "definition": record.definition,
                "aliases": record.aliases or [],
                "confidenceScore": record.confidence_score,
                "sourceId": record.source_id,
                "pageId": record.page_id,
            }
        )
    return mapping


def _page_type_candidates(related_source_ids: list[str], source_metadata: dict[str, dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for source_id in related_source_ids:
        metadata = source_metadata.get(source_id) or {}
        for candidate in metadata.get("pageTypeCandidates", []):
            page_type = candidate.get("pageType")
            if not page_type:
                continue
            current = merged.get(page_type)
            if current is None or float(candidate.get("confidence", 0)) > float(current.get("confidence", 0)):
                merged[page_type] = {
                    "pageType": page_type,
                    "confidence": float(candidate.get("confidence", 0)),
                    "reason": str(candidate.get("reason") or ""),
                }
    return sorted(merged.values(), key=lambda item: item["confidence"], reverse=True)


def _page_sources_metadata(db: Session, source_ids: list[str]) -> dict[str, dict]:
    if not source_ids:
        return {}
    from app.models import Source

    return {source.id: source.metadata_json or {} for source in db.query(Source).filter(Source.id.in_(source_ids)).all()}


def _page_backlinks_map(db: Session, page_ids: list[str]) -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {page_id: [] for page_id in page_ids}
    if not page_ids:
        return mapping

    pages = {page.id: page for page in db.query(Page).filter(Page.id.in_(page_ids)).all()}
    page_links = db.query(PageLink).filter(PageLink.to_page_id.in_(page_ids)).all()
    referring_ids = [link.from_page_id for link in page_links]
    ref_pages = {page.id: page for page in db.query(Page).filter(Page.id.in_(referring_ids)).all()} if referring_ids else {}

    for link in page_links:
        ref_page = ref_pages.get(link.from_page_id)
        if not ref_page:
            continue
        mapping.setdefault(link.to_page_id, []).append(
            {"id": ref_page.id, "slug": ref_page.slug, "title": ref_page.title, "relationType": link.relation_type}
        )

    for ref_page in db.query(Page).filter(Page.related_page_ids.isnot(None)).all():
        for target_id in ref_page.related_page_ids or []:
            if target_id not in mapping:
                continue
            entry = {"id": ref_page.id, "slug": ref_page.slug, "title": ref_page.title, "relationType": "related_to"}
            if entry not in mapping[target_id]:
                mapping[target_id].append(entry)

    for page_id in page_ids:
        mapping[page_id] = sorted(mapping.get(page_id, []), key=lambda item: item["title"].lower())
    return mapping


def _page_citations_map(db: Session, page_ids: list[str]) -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {page_id: [] for page_id in page_ids}
    if not page_ids:
        return mapping

    rows = (
        db.query(PageClaimLink, Claim, SourceChunk, Source)
        .join(Claim, Claim.id == PageClaimLink.claim_id)
        .join(SourceChunk, SourceChunk.id == Claim.source_chunk_id)
        .join(Source, Source.id == SourceChunk.source_id)
        .filter(PageClaimLink.page_id.in_(page_ids))
        .order_by(PageClaimLink.page_id.asc(), PageClaimLink.section_key.asc(), Claim.extracted_at.asc())
        .all()
    )

    counters: dict[str, int] = {}
    for link, claim, chunk, source in rows:
        counters[link.page_id] = counters.get(link.page_id, 0) + 1
        snippet = claim.text or chunk.content[:280]
        chunk_span_start = claim.evidence_span_start if claim.evidence_span_start is not None else 0
        chunk_span_end = claim.evidence_span_end if claim.evidence_span_end is not None else len(chunk.content or "")
        mapping.setdefault(link.page_id, []).append(
            {
                "id": link.id,
                "index": counters[link.page_id],
                "claimId": claim.id,
                "claimText": claim.text,
                "sectionKey": link.section_key,
                "citationStyle": link.citation_style,
                "sourceId": source.id,
                "sourceTitle": source.title,
                "chunkId": chunk.id,
                "chunkIndex": chunk.chunk_index,
                "chunkSectionTitle": chunk.section_title,
                "pageNumber": chunk.page_number,
                "snippet": snippet[:500],
                "chunkSpanStart": chunk_span_start,
                "chunkSpanEnd": chunk_span_end,
                "sourceSpanStart": chunk.span_start + chunk_span_start,
                "sourceSpanEnd": chunk.span_start + chunk_span_end,
                "confidence": claim.confidence_score,
            }
        )
    return mapping


def serialize_page(
    page: Page,
    related_source_ids: list[str],
    source_metadata: dict[str, dict] | None = None,
    backlinks: list[dict] | None = None,
    citations: list[dict] | None = None,
    timeline_events: list[dict] | None = None,
    glossary_terms: list[dict] | None = None,
) -> dict:
    return {
        "id": page.id,
        "slug": page.slug,
        "title": page.title,
        "pageType": page.page_type,
        "status": page.status,
        "summary": page.summary,
        "contentMd": page.content_md,
        "contentJson": page.content_json or markdown_to_blocks(page.content_md),
        "contentHtml": page.content_html,
        "currentVersion": page.current_version,
        "lastComposedAt": _iso(page.last_composed_at),
        "lastReviewedAt": _iso(page.last_reviewed_at),
        "publishedAt": _iso(page.published_at),
        "owner": page.owner,
        "tags": page.tags or [],
        "parentPageId": page.parent_page_id,
        "keyFacts": page.key_facts or [],
        "relatedSourceIds": related_source_ids,
        "relatedPageIds": page.related_page_ids or [],
        "relatedEntityIds": page.related_entity_ids or [],
        "collectionId": page.collection_id,
        "backlinks": backlinks or [],
        "citations": citations or [],
        "pageTypeCandidates": _page_type_candidates(related_source_ids, source_metadata or {}),
        "timelineEvents": timeline_events or [],
        "glossaryTerms": glossary_terms or [],
    }


def list_pages(db: Session, page: int = 1, page_size: int = 20, status: str | None = None, page_type: str | None = None, search: str | None = None, sort: str | None = None, collection_id: str | None = None, actor=None) -> dict:
    query = db.query(Page)
    if actor is not None:
        query = apply_collection_scope_filter(query, Page, actor)
    if status:
        query = query.filter(Page.status == status)
    if page_type:
        query = query.filter(Page.page_type == page_type)
    if collection_id:
        if collection_id == "standalone":
            query = query.filter(Page.collection_id.is_(None))
        else:
            query = query.filter(Page.collection_id == collection_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((Page.title.ilike(term)) | (Page.slug.ilike(term)) | (Page.summary.ilike(term)))

    if sort == "title":
        query = query.order_by(Page.title.asc())
    elif sort == "status":
        query = query.order_by(Page.status.asc(), Page.title.asc())
    elif sort == "type":
        query = query.order_by(Page.page_type.asc(), Page.title.asc())
    else:
        query = query.order_by(Page.last_composed_at.desc())

    items = query.all()
    page_ids = [item.id for item in items]
    source_map = _page_source_map(db, page_ids)
    source_metadata = _page_sources_metadata(db, sorted({source_id for values in source_map.values() for source_id in values}))
    backlinks_map = _page_backlinks_map(db, page_ids)
    citations_map = _page_citations_map(db, page_ids)
    timeline_map = _page_timeline_map(db, page_ids)
    glossary_map = _page_glossary_map(db, page_ids)
    start = (page - 1) * page_size
    data = [
        serialize_page(
            item,
            source_map.get(item.id, []),
            source_metadata=source_metadata,
            backlinks=backlinks_map.get(item.id, []),
            citations=citations_map.get(item.id, []),
            timeline_events=timeline_map.get(item.id, []),
            glossary_terms=glossary_map.get(item.id, []),
        )
        for item in items[start : start + page_size]
    ]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def get_page_by_slug(db: Session, slug: str, actor=None) -> dict | None:
    page = db.query(Page).filter(Page.slug == slug).first()
    if not page:
        return None
    if actor is not None and not can_access_collection_id(actor, page.collection_id):
        return None
    source_map = _page_source_map(db, [page.id])
    related_source_ids = source_map.get(page.id, [])
    source_metadata = _page_sources_metadata(db, related_source_ids)
    backlinks_map = _page_backlinks_map(db, [page.id])
    citations_map = _page_citations_map(db, [page.id])
    timeline_map = _page_timeline_map(db, [page.id])
    glossary_map = _page_glossary_map(db, [page.id])
    return serialize_page(
        page,
        related_source_ids,
        source_metadata=source_metadata,
        backlinks=backlinks_map.get(page.id, []),
        citations=citations_map.get(page.id, []),
        timeline_events=timeline_map.get(page.id, []),
        glossary_terms=glossary_map.get(page.id, []),
    )


def get_page_by_id(db: Session, page_id: str, actor=None) -> Page | None:
    page = db.query(Page).filter(Page.id == page_id).first()
    if page and actor is not None and not can_access_collection_id(actor, page.collection_id):
        return None
    return page


def get_page_versions(db: Session, page_id: str) -> list[dict]:
    versions = db.query(PageVersion).filter(PageVersion.page_id == page_id).order_by(PageVersion.version_no.desc()).all()
    return [
        {
            "id": version.id,
            "pageId": version.page_id,
            "versionNo": version.version_no,
            "contentMd": version.content_md,
            "changeSummary": version.change_summary,
            "createdAt": _iso(version.created_at),
            "createdByAgentOrUser": version.created_by_agent_or_user,
            "reviewStatus": version.review_status,
        }
        for version in versions
    ]


def get_page_audit_logs(db: Session, page_id: str, limit: int = 50) -> list[dict]:
    return list_audit_logs(db, object_type="page", object_id=page_id, limit=limit)


def get_page_diff(db: Session, page_id: str, version_no: int) -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    version = db.query(PageVersion).filter(PageVersion.page_id == page_id, PageVersion.version_no == version_no).first()
    return {"old": version.content_md if version else "", "new": page.content_md}


def _unique_slug(db: Session, base: str) -> str:
    root = "-".join(base.strip().lower().split()) or f"page-{uuid4().hex[:6]}"
    root = "".join(char if char.isalnum() or char == "-" else "-" for char in root)
    while "--" in root:
        root = root.replace("--", "-")
    root = root.strip("-") or f"page-{uuid4().hex[:6]}"
    candidate = root
    suffix = 1
    while db.query(Page).filter(Page.slug == candidate).first():
        suffix += 1
        candidate = f"{root}-{suffix}"
    return candidate


def list_entities(db: Session, page: int = 1, page_size: int = 50, search: str | None = None, entity_type: str | None = None) -> dict:
    from app.models import Entity, SourceEntityLink

    query = db.query(Entity)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((Entity.name.ilike(term)) | (Entity.description.ilike(term)))
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    items = query.order_by(Entity.name.asc()).all()
    start = (page - 1) * page_size
    paged = items[start : start + page_size]
    data = []
    for entity in paged:
        source_count = db.query(SourceEntityLink).filter(SourceEntityLink.entity_id == entity.id).count()
        page_count = db.query(PageEntityLink).filter(PageEntityLink.entity_id == entity.id).count()
        data.append(
            {
                "id": entity.id,
                "name": entity.name,
                "entityType": entity.entity_type,
                "description": entity.description,
                "aliases": entity.aliases or [],
                "normalizedName": entity.normalized_name,
                "createdAt": _iso(entity.created_at),
                "sourceCount": source_count,
                "pageCount": page_count,
            }
        )
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def list_timeline_events(db: Session, page: int = 1, page_size: int = 50, search: str | None = None) -> dict:
    query = db.query(TimelineEvent)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((TimelineEvent.title.ilike(term)) | (TimelineEvent.description.ilike(term)))
    items = query.order_by(TimelineEvent.sort_key.asc(), TimelineEvent.title.asc()).all()
    start = (page - 1) * page_size
    data = [
        {
            "id": item.id,
            "eventDate": item.event_date,
            "sortKey": item.sort_key,
            "title": item.title,
            "description": item.description,
            "precision": item.precision,
            "entityIds": item.entity_ids or [],
            "sourceId": item.source_id,
            "pageId": item.page_id,
        }
        for item in items[start : start + page_size]
    ]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def list_glossary_terms(db: Session, page: int = 1, page_size: int = 50, search: str | None = None) -> dict:
    query = db.query(GlossaryTerm)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter((GlossaryTerm.term.ilike(term)) | (GlossaryTerm.definition.ilike(term)))
    items = query.order_by(GlossaryTerm.term.asc()).all()
    start = (page - 1) * page_size
    data = [
        {
            "id": item.id,
            "term": item.term,
            "normalizedTerm": item.normalized_term,
            "definition": item.definition,
            "aliases": item.aliases or [],
            "confidenceScore": item.confidence_score,
            "sourceId": item.source_id,
            "pageId": item.page_id,
        }
        for item in items[start : start + page_size]
    ]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def publish_page(db: Session, page_id: str, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    now = datetime.now(timezone.utc)
    page.status = "published"
    page.published_at = now
    page.last_reviewed_at = now
    create_audit_log(
        db,
        action="publish",
        object_type="page",
        object_id=page.id,
        actor=actor,
        summary=f"Published page `{page.title}`",
        metadata={"slug": page.slug, "versionNo": page.current_version, **(actor_metadata or {})},
    )
    db.commit()
    return get_page_by_slug(db, page.slug)


def unpublish_page(db: Session, page_id: str, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    page.status = "draft"
    page.published_at = None
    page.last_composed_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="unpublish",
        object_type="page",
        object_id=page.id,
        actor=actor,
        summary=f"Unpublished page `{page.title}`",
        metadata={"slug": page.slug, "versionNo": page.current_version, **(actor_metadata or {})},
    )
    db.commit()
    return get_page_by_slug(db, page.slug)


def update_page_content(
    db: Session,
    page_id: str,
    content_md: str | None,
    change_summary: str | None = None,
    author: str = "Current User",
    expected_version: int | None = None,
    content_json: list[dict] | None = None,
) -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    if expected_version is not None and page.current_version != expected_version:
        raise PageEditConflict(page.current_version)

    normalized_md, normalized_blocks = normalize_page_document(content_md, content_json)
    now = datetime.now(timezone.utc)
    summary, key_facts = summarize_text(page.title, normalized_md[:16000])
    page.content_md = normalized_md
    page.content_json = normalized_blocks
    page.summary = summary
    page.key_facts = key_facts
    page.tags = build_tags(page.title, normalized_md)
    page.status = "draft" if page.status == "published" else page.status
    page.last_composed_at = now
    page.current_version += 1

    version = PageVersion(
        id=f"pv-{uuid4().hex[:8]}",
        page_id=page.id,
        version_no=page.current_version,
        content_md=normalized_md,
        change_summary=(change_summary or "Manual draft update")[:255],
        created_at=now,
        created_by_agent_or_user=author,
        review_status="needs_revision",
    )
    db.add(version)
    create_audit_log(
        db,
        action="update_content",
        object_type="page",
        object_id=page.id,
        actor=author,
        summary=(change_summary or "Manual draft update")[:255],
        metadata={"slug": page.slug, "versionNo": page.current_version, "previousStatus": "published" if page.status == "draft" else page.status},
    )
    db.commit()
    return get_page_by_slug(db, page.slug)


def restore_page_version(db: Session, page_id: str, version_no: int, author: str = "Current User") -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    version = db.query(PageVersion).filter(PageVersion.page_id == page_id, PageVersion.version_no == version_no).first()
    if not version:
        return None
    return update_page_content(
        db,
        page_id,
        version.content_md,
        change_summary=f"Restored version {version_no}",
        author=author,
        expected_version=page.current_version,
    )


def bulk_update_pages(db: Session, page_ids: list[str], action: str, actor: str = "Current User", actor_metadata: dict | None = None) -> dict:
    updated: list[str] = []
    skipped: list[str] = []
    for page_id in page_ids:
        if action == "publish":
            result = publish_page(db, page_id, actor=actor, actor_metadata=actor_metadata)
        elif action == "unpublish":
            result = unpublish_page(db, page_id, actor=actor, actor_metadata=actor_metadata)
        else:
            result = None
        if result:
            updated.append(page_id)
        else:
            skipped.append(page_id)
    return {"success": True, "action": action, "updatedCount": len(updated), "updatedIds": updated, "skippedIds": skipped}


def create_page_from_chunks(
    db: Session,
    *,
    title: str,
    chunk_ids: list[str],
    owner: str,
    existing_page_id: str | None = None,
) -> dict | None:
    chunks = db.query(SourceChunk).filter(SourceChunk.id.in_(chunk_ids)).order_by(SourceChunk.chunk_index.asc()).all()
    if not chunks:
        return None
    source_ids = sorted({chunk.source_id for chunk in chunks})
    lines = [f"# {title.strip()}", "", "## Source Notes", ""]
    for chunk in chunks:
        heading = chunk.section_title or f"Chunk {chunk.chunk_index}"
        lines.extend([f"### {heading}", "", chunk.content.strip(), "", f"> Source chunk: `{chunk.id}`", ""])
    content_md = "\n".join(lines).strip()
    summary, key_facts = summarize_text(title, content_md[:16000])
    if existing_page_id:
        page = get_page_by_id(db, existing_page_id)
        if not page:
            return None
        updated = update_page_content(db, page.id, content_md, "Updated from selected source chunks", author=owner, expected_version=page.current_version)
        existing_sources = set(_page_source_map(db, [page.id]).get(page.id, []))
        for source_id in source_ids:
            if source_id not in existing_sources:
                db.add(PageSourceLink(id=f"psl-{uuid4().hex[:8]}", page_id=page.id, source_id=source_id))
        db.commit()
        return get_page_by_slug(db, updated["slug"]) if updated else None
    page = create_page_with_version(
        db,
        title=title.strip(),
        slug=_unique_slug(db, title),
        summary=summary,
        content_md=content_md,
        owner=owner,
        page_type="summary",
        status="draft",
        tags=build_tags(title, content_md),
        key_facts=key_facts,
        related_source_ids=source_ids,
        related_entity_ids=[],
    )
    create_audit_log(
        db,
        action="create_from_chunks",
        object_type="page",
        object_id=page.id,
        actor=owner,
        summary=f"Created draft page `{title}` from selected source chunks",
        metadata={"chunkIds": chunk_ids, "sourceIds": source_ids},
    )
    db.commit()
    return get_page_by_slug(db, page.slug)


def build_editor_insert_helpers(db: Session, page_id: str, source_id: str | None = None, chunk_id: str | None = None) -> dict | None:
    page = get_page_by_id(db, page_id)
    if not page:
        return None
    backlinks = _page_backlinks_map(db, [page_id]).get(page_id, [])
    citations = _page_citations_map(db, [page_id]).get(page_id, [])
    if source_id:
        citations = [item for item in citations if item["sourceId"] == source_id]
    if chunk_id:
        citations = [item for item in citations if item["chunkId"] == chunk_id]
    return {
        "pageId": page_id,
        "backlinks": [
            {"pageId": item["id"], "title": item["title"], "markdown": f"[[{item['title']}]]"}
            for item in backlinks
        ],
        "citations": [
            {
                "sourceId": item["sourceId"],
                "chunkId": item["chunkId"],
                "label": f"{item['sourceTitle']} chunk {item['chunkIndex']}",
                "markdown": f"[^{item['index']}]: {item['sourceTitle']} / chunk {item['chunkIndex']} - {item['snippet'][:180]}",
            }
            for item in citations
        ],
    }


def compose_page(
    db: Session,
    topic: str,
    source_ids: list[str] | None = None,
    *,
    content_md: str | None = None,
    content_json: list[dict] | None = None,
    collection_id: str | None = None,
    page_type: str = "summary",
) -> dict:
    normalized_topic = topic.strip()
    slug = "-".join(normalized_topic.lower().split())
    unique_slug = slug
    suffix = 1
    while db.query(Page).filter(Page.slug == unique_slug).first():
        suffix += 1
        unique_slug = f"{slug}-{suffix}"

    source_ids = [source_id for source_id in (source_ids or []) if source_id]
    resolved_collection_id = collection_id
    if source_ids and resolved_collection_id is None:
        linked_source = db.query(PageSourceLink).filter(PageSourceLink.source_id.in_(source_ids)).first()
        if linked_source:
            linked_page = db.query(Page).filter(Page.id == linked_source.page_id).first()
            resolved_collection_id = linked_page.collection_id if linked_page else None
        if resolved_collection_id is None:
            from app.models import Source

            source_record = db.query(Source).filter(Source.id.in_(source_ids), Source.collection_id.is_not(None)).first()
            resolved_collection_id = source_record.collection_id if source_record else None
    source_section = "\n".join(f"- Source: {source_id}" for source_id in source_ids) if source_ids else "- No linked sources yet."
    default_content_md = "\n".join(
        [
            f"# {normalized_topic}",
            "",
            "## Draft Summary",
            "",
            f"This is an initial draft page for {normalized_topic}. Refine the content and add citations before publishing.",
            "",
            "## Linked Sources",
            "",
            source_section,
        ]
    )
    draft_content_md, draft_content_json = normalize_page_document(content_md or default_content_md, content_json)
    if (content_md and content_md.strip()) or content_json:
        summary = _lightweight_summary(draft_content_md, normalized_topic)
        key_facts: list[str] = []
    else:
        summary, key_facts = summarize_text(normalized_topic, draft_content_md)
    page = create_page_with_version(
        db,
        title=normalized_topic,
        slug=unique_slug,
        summary=summary,
        content_md=draft_content_md,
        content_json=draft_content_json,
        owner="Current User",
        page_type=page_type,
        status="draft",
        tags=build_tags(normalized_topic, normalized_topic if content_md else draft_content_md),
        key_facts=key_facts,
        related_source_ids=source_ids,
        related_entity_ids=[],
        collection_id=resolved_collection_id,
    )
    create_audit_log(
        db,
        action="compose",
        object_type="page",
        object_id=page.id,
        actor="Current User",
        summary=f"Composed draft page `{page.title}`",
        metadata={"slug": page.slug, "sourceIds": source_ids, "collectionId": resolved_collection_id, "directDraft": bool(content_md or content_json)},
    )
    db.commit()
    return get_page_by_slug(db, page.slug)


def create_page_with_version(
    db: Session,
    *,
    title: str,
    slug: str,
    summary: str,
    content_md: str,
    content_json: list[dict] | None = None,
    owner: str,
    page_type: str,
    status: str,
    tags: list[str],
    key_facts: list[str],
    related_source_ids: list[str],
    related_entity_ids: list[str],
    collection_id: str | None = None,
) -> Page:
    now = datetime.now(timezone.utc)
    page = Page(
        id=f"page-{uuid4().hex[:8]}",
        slug=slug,
        title=title,
        page_type=page_type,
        status=status,
        summary=summary,
        content_md=content_md,
        content_json=content_json or markdown_to_blocks(content_md),
        content_html=None,
        current_version=1,
        last_composed_at=now,
        last_reviewed_at=None,
        published_at=None,
        owner=owner,
        tags=tags,
        parent_page_id=None,
        key_facts=key_facts,
        related_page_ids=[],
        related_entity_ids=related_entity_ids,
        collection_id=collection_id,
    )
    db.add(page)
    db.flush()

    version = PageVersion(
        id=f"pv-{uuid4().hex[:8]}",
        page_id=page.id,
        version_no=1,
        content_md=content_md,
        change_summary="Initial page generated from source ingestion",
        created_at=now,
        created_by_agent_or_user="Ingest Pipeline",
        review_status="needs_revision",
    )
    db.add(version)
    for source_id in related_source_ids:
        db.add(PageSourceLink(id=f"psl-{uuid4().hex[:8]}", page_id=page.id, source_id=source_id))
    create_audit_log(
        db,
        action="create",
        object_type="page",
        object_id=page.id,
        actor=owner,
        summary=f"Created page `{title}`",
        metadata={"slug": slug, "sourceIds": related_source_ids, "collectionId": collection_id, "pageType": page_type},
    )
    db.flush()
    return page
