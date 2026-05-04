from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import urllib.error
import urllib.request
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.embedding_client import embedding_client
from app.core.connectors import connector_error, get_connector_capability, list_connector_capabilities
from app.core.ingest import (
    build_page_markdown,
    ensure_upload_dir,
    extract_readable_html,
    infer_mime_type,
    infer_source_type,
    prompt_metadata,
    run_ingest_pipeline,
    serialize_stage_results,
    slugify,
)
from app.core.reliability import PROMPT_VERSION
from app.core.runtime_config import load_runtime_snapshot
from app.core.storage import replace_source_bytes, save_source_bytes
from app.models import Claim, Collection, Entity, ExtractionRun, GlossaryTerm, KnowledgeUnit, Page, PageClaimLink, PageEntityLink, PageSourceLink, Source, SourceChunk, SourceEntityLink, SourceSuggestion, TimelineEvent
from app.models import ReviewIssue, ReviewItem
from app.services.pages import create_page_with_version
from app.services.suggestions import create_source_suggestion


ALLOWED_PAGE_TYPES = {"summary", "overview", "deep_dive", "entity", "source_derived", "faq", "glossary", "timeline", "sop", "concept", "issue"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_CONNECTOR_BYTES = 2 * 1024 * 1024
MAX_TEXT_BYTES = 1024 * 1024
MIN_TEXT_CHARS = 20


def _primary_page_type(candidates: list[dict]) -> str:
    sorted_candidates = sorted(candidates, key=lambda item: float(item.get("confidence", 0)), reverse=True)
    for candidate in sorted_candidates:
        page_type = str(candidate.get("pageType") or "")
        if page_type and page_type != "summary" and page_type in ALLOWED_PAGE_TYPES:
            return page_type
    top = str(sorted_candidates[0].get("pageType") or "summary") if sorted_candidates else "summary"
    return top if top in ALLOWED_PAGE_TYPES else "source_derived"


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _serialize_source(source: Source) -> dict:
    return {
        "id": source.id,
        "title": source.title,
        "sourceType": source.source_type,
        "mimeType": source.mime_type,
        "filePath": source.file_path,
        "url": source.url,
        "uploadedAt": _iso(source.uploaded_at),
        "updatedAt": _iso(source.updated_at),
        "createdBy": source.created_by,
        "parseStatus": source.parse_status,
        "ingestStatus": source.ingest_status,
        "metadataJson": source.metadata_json or {},
        "checksum": source.checksum,
        "trustLevel": source.trust_level,
        "fileSize": source.file_size,
        "description": source.description,
        "tags": source.tags or [],
        "collectionId": source.collection_id,
    }


def _paginate(items: list[dict], page: int, page_size: int) -> dict:
    start = (page - 1) * page_size
    data = items[start : start + page_size]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def list_sources(db: Session, page: int = 1, page_size: int = 20, status: str | None = None, source_type: str | None = None, search: str | None = None, collection_id: str | None = None) -> dict:
    query = db.query(Source)
    if status and status != "archived":
        query = query.filter(Source.parse_status == status)
    if source_type:
        query = query.filter(Source.source_type == source_type)
    if collection_id:
        if collection_id == "standalone":
            query = query.filter(Source.collection_id.is_(None))
        else:
            query = query.filter(Source.collection_id == collection_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Source.title.ilike(term), Source.description.ilike(term)))
    items = query.order_by(Source.uploaded_at.desc()).all()
    if status == "archived":
        items = [item for item in items if bool((item.metadata_json or {}).get("archived"))]
    else:
        items = [item for item in items if not bool((item.metadata_json or {}).get("archived"))]
    return _paginate([_serialize_source(item) for item in items], page, page_size)


def get_source_by_id(db: Session, source_id: str) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    return _serialize_source(source) if source else None


def archive_source(db: Session, source_id: str, actor: str = "Current User") -> dict | None:
    from app.services.audit import create_audit_log

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    metadata = dict(source.metadata_json or {})
    metadata["archived"] = True
    metadata["archivedAt"] = datetime.now(timezone.utc).isoformat()
    source.metadata_json = metadata
    source.updated_at = datetime.now(timezone.utc)
    linked_page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id == source_id).all()]
    create_audit_log(
        db,
        action="archive_source",
        object_type="source",
        object_id=source.id,
        actor=actor,
        summary=f"Archived source `{source.title}` without deleting page links or versions",
        metadata={"linkedPageIds": linked_page_ids},
    )
    for page_id in linked_page_ids:
        create_audit_log(
            db,
            action="source_archived",
            object_type="page",
            object_id=page_id,
            actor=actor,
            summary=f"Linked source `{source.title}` was archived",
            metadata={"sourceId": source.id},
        )
    db.commit()
    db.refresh(source)
    return _serialize_source(source)


def restore_source(db: Session, source_id: str, actor: str = "Current User") -> dict | None:
    from app.services.audit import create_audit_log

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    metadata = dict(source.metadata_json or {})
    metadata["archived"] = False
    metadata["restoredAt"] = datetime.now(timezone.utc).isoformat()
    source.metadata_json = metadata
    source.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="restore_source",
        object_type="source",
        object_id=source.id,
        actor=actor,
        summary=f"Restored source `{source.title}`",
        metadata={},
    )
    db.commit()
    db.refresh(source)
    return _serialize_source(source)


def get_source_chunks(db: Session, source_id: str, page: int = 1, page_size: int = 20) -> dict:
    chunks = db.query(SourceChunk).filter(SourceChunk.source_id == source_id).order_by(SourceChunk.chunk_index.asc()).all()
    data = [
        {
            "id": chunk.id,
            "sourceId": chunk.source_id,
            "chunkIndex": chunk.chunk_index,
            "sectionTitle": chunk.section_title,
            "pageNumber": chunk.page_number,
            "content": chunk.content,
            "tokenCount": chunk.token_count,
            "embeddingId": chunk.embedding_id,
            "metadataJson": chunk.metadata_json or {},
            "spanStart": chunk.span_start,
            "spanEnd": chunk.span_end,
            "createdAt": _iso(chunk.created_at),
        }
        for chunk in chunks
    ]
    return _paginate(data, page, page_size)


def get_source_claims(db: Session, source_id: str) -> list[dict]:
    claims = db.query(Claim).join(SourceChunk, Claim.source_chunk_id == SourceChunk.id).filter(SourceChunk.source_id == source_id).order_by(Claim.extracted_at.desc()).all()
    return [
        {
            "id": claim.id,
            "text": claim.text,
            "claimType": claim.claim_type,
            "confidenceScore": claim.confidence_score,
            "sourceChunkIds": [claim.source_chunk_id],
            "canonicalStatus": claim.canonical_status,
            "reviewStatus": claim.review_status,
            "extractedAt": _iso(claim.extracted_at),
            "topic": claim.topic,
            "extractionMethod": claim.extraction_method,
            "evidenceSpanStart": claim.evidence_span_start,
            "evidenceSpanEnd": claim.evidence_span_end,
            "metadataJson": claim.metadata_json or {},
        }
        for claim in claims
    ]


def get_source_knowledge_units(db: Session, source_id: str) -> list[dict]:
    units = (
        db.query(KnowledgeUnit)
        .filter(KnowledgeUnit.source_id == source_id)
        .order_by(KnowledgeUnit.created_at.desc(), KnowledgeUnit.confidence_score.desc())
        .all()
    )
    return [
        {
            "id": unit.id,
            "sourceId": unit.source_id,
            "sourceChunkId": unit.source_chunk_id,
            "claimId": unit.claim_id,
            "unitType": unit.unit_type,
            "title": unit.title,
            "text": unit.text,
            "status": unit.status,
            "reviewStatus": unit.review_status,
            "canonicalStatus": unit.canonical_status,
            "confidenceScore": unit.confidence_score,
            "topic": unit.topic,
            "entityIds": unit.entity_ids or [],
            "evidenceSpanStart": unit.evidence_span_start,
            "evidenceSpanEnd": unit.evidence_span_end,
            "metadataJson": unit.metadata_json or {},
            "createdAt": _iso(unit.created_at),
            "updatedAt": _iso(unit.updated_at),
        }
        for unit in units
    ]


def get_source_extraction_runs(db: Session, source_id: str) -> list[dict]:
    runs = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.source_id == source_id)
        .order_by(ExtractionRun.started_at.desc())
        .all()
    )
    return [
        {
            "id": run.id,
            "sourceId": run.source_id,
            "runType": run.run_type,
            "status": run.status,
            "method": run.method,
            "taskProfile": run.task_profile,
            "modelProvider": run.model_provider,
            "modelName": run.model_name,
            "promptVersion": run.prompt_version,
            "inputChunkCount": run.input_chunk_count,
            "outputCount": run.output_count,
            "errorMessage": run.error_message,
            "metadataJson": run.metadata_json or {},
            "startedAt": _iso(run.started_at),
            "finishedAt": _iso(run.finished_at),
        }
        for run in runs
    ]


def get_source_entities(db: Session, source_id: str) -> list[dict]:
    claims = db.query(Claim).join(SourceChunk, Claim.source_chunk_id == SourceChunk.id).filter(SourceChunk.source_id == source_id).all()
    entity_ids = sorted({entity_id for claim in claims for entity_id in (claim.entity_ids or [])})
    if not entity_ids:
        return []
    entities = db.query(Entity).filter(Entity.id.in_(entity_ids)).order_by(Entity.name.asc()).all()
    return [
        {
            "id": entity.id,
            "name": entity.name,
            "entityType": entity.entity_type,
            "description": entity.description,
            "aliases": entity.aliases or [],
            "normalizedName": entity.normalized_name,
            "createdAt": _iso(entity.created_at),
        }
        for entity in entities
    ]


def get_source_pages(db: Session, source_id: str) -> list[dict]:
    pages = db.query(Page).join(PageSourceLink, PageSourceLink.page_id == Page.id).filter(PageSourceLink.source_id == source_id).order_by(Page.last_composed_at.desc()).all()
    related_map = {}
    if pages:
        for page_id, linked_source_id in db.query(PageSourceLink.page_id, PageSourceLink.source_id).filter(PageSourceLink.page_id.in_([page.id for page in pages])).all():
            related_map.setdefault(page_id, []).append(linked_source_id)
    return [
        {
            "id": page.id,
            "slug": page.slug,
            "title": page.title,
            "pageType": page.page_type,
            "status": page.status,
            "summary": page.summary,
            "contentMd": page.content_md,
            "contentHtml": page.content_html,
            "currentVersion": page.current_version,
            "lastComposedAt": _iso(page.last_composed_at),
            "lastReviewedAt": _iso(page.last_reviewed_at),
            "publishedAt": _iso(page.published_at),
            "owner": page.owner,
            "tags": page.tags or [],
            "parentPageId": page.parent_page_id,
            "keyFacts": page.key_facts or [],
            "relatedSourceIds": related_map.get(page.id, []),
            "relatedPageIds": page.related_page_ids or [],
            "relatedEntityIds": page.related_entity_ids or [],
            "collectionId": page.collection_id,
        }
        for page in pages
    ]


def _suggest_collection(db: Session, title: str, tags: list[str]) -> str | None:
    collections = db.query(Collection).all()
    if not collections:
        return None
    haystack_terms = set(slugify(" ".join([title, *tags])).split("-"))
    best: tuple[int, str | None] = (0, None)
    for collection in collections:
        collection_terms = set(slugify(" ".join([collection.name, collection.description or ""])).split("-"))
        score = len(haystack_terms & collection_terms)
        if score > best[0]:
            best = (score, collection.id)
    return best[1]


def _rank_page_suggestions(db: Session, title: str, summary: str, tags: list[str], exclude_slug: str | None = None) -> list[tuple[Page, float, list[str]]]:
    terms = {term for term in slugify(" ".join([title, summary, *tags])).split("-") if len(term) > 3}
    ranked: list[tuple[Page, float, list[str]]] = []
    for page in db.query(Page).all():
        if exclude_slug and page.slug == exclude_slug:
            continue
        page_terms = {term for term in slugify(" ".join([page.title, page.summary or "", " ".join(page.tags or [])])).split("-") if len(term) > 3}
        matches = sorted(terms & page_terms)
        if not matches:
            continue
        confidence = min(0.95, 0.45 + (len(matches) / max(len(terms), 1)))
        ranked.append((page, confidence, matches[:8]))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:3]


def _unique_page_slug(db: Session, base: str) -> str:
    slug = slugify(base) or f"page-{uuid4().hex[:6]}"
    unique = slug
    suffix = 1
    while db.query(Page).filter(Page.slug == unique).first():
        suffix += 1
        unique = f"{slug}-{suffix}"
    return unique


def _create_extraction_run(
    db: Session,
    *,
    source_id: str,
    run_type: str,
    status: str,
    method: str,
    task_profile: str,
    model_provider: str,
    model_name: str,
    input_chunk_count: int,
    output_count: int,
    metadata_json: dict | None,
    started_at: datetime,
    finished_at: datetime,
    error_message: str | None = None,
) -> None:
    db.add(
        ExtractionRun(
            id=f"er-{uuid4().hex[:8]}",
            source_id=source_id,
            run_type=run_type,
            status=status,
            method=method,
            task_profile=task_profile,
            model_provider=model_provider or "none",
            model_name=model_name or "",
            prompt_version=PROMPT_VERSION,
            input_chunk_count=input_chunk_count,
            output_count=output_count,
            error_message=error_message,
            metadata_json=metadata_json or {},
            started_at=started_at,
            finished_at=finished_at,
        )
    )


def _derive_claim_run_method(generated_claims: list[dict]) -> str:
    methods = {str(item.get("extraction_method") or "").strip().lower() for item in generated_claims if item.get("extraction_method")}
    methods.discard("")
    if not methods:
        return "heuristic"
    if len(methods) > 1:
        return "hybrid"
    return next(iter(methods))


def create_source_record(
    db: Session,
    filename: str,
    mime_type: str,
    file_size: int | None,
    file_bytes: bytes,
    collection_id: str | None = None,
    actor: str = "Current User",
    source_type: str | None = None,
    source_url: str | None = None,
    metadata: dict | None = None,
    description: str | None = None,
    title: str | None = None,
) -> tuple[Source, Path]:
    timestamp = datetime.now(timezone.utc)
    resolved_source_type = source_type or infer_source_type(filename)
    resolved_mime_type = infer_mime_type(filename, mime_type)
    stored_path = save_source_bytes(filename, file_bytes)
    checksum = hashlib.sha256(file_bytes).hexdigest()
    duplicate_source = db.query(Source).filter(Source.checksum == checksum).order_by(Source.uploaded_at.asc()).first()
    enriched_metadata = {
        **(metadata or {}),
        "storage": {"backend": "local", "path": str(stored_path)},
        "dedupe": {"checksum": checksum, "duplicateOfSourceId": duplicate_source.id if duplicate_source else None},
    }

    source = Source(
        id=f"src-{uuid4().hex[:8]}",
        title=title or filename,
        source_type=resolved_source_type,
        mime_type=resolved_mime_type,
        file_path=str(stored_path),
        url=source_url,
        uploaded_at=timestamp,
        updated_at=timestamp,
        created_by=actor,
        parse_status="parsing",
        ingest_status="parsing",
        metadata_json=enriched_metadata,
        checksum=checksum,
        trust_level="medium",
        file_size=file_size,
        description=description or "Uploaded source is being processed.",
        tags=[],
        collection_id=collection_id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source, stored_path


def get_connector_registry() -> list[dict]:
    return list_connector_capabilities()


def _validate_collection(db: Session, collection_id: str | None) -> None:
    if collection_id and not db.query(Collection.id).filter(Collection.id == collection_id).first():
        raise ValueError("Collection not found")


def _safe_connector_filename(title: str, suffix: str) -> str:
    stem = slugify(title) or f"source-{uuid4().hex[:6]}"
    return f"{stem[:90]}{suffix}"


def create_text_source_record(
    db: Session,
    *,
    title: str,
    content: str,
    source_type: str = "txt",
    collection_id: str | None = None,
    actor: str = "Current User",
) -> tuple[Source, Path]:
    normalized_title = " ".join(title.strip().split())
    normalized_content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_title:
        raise ValueError("Title is required")
    if len(normalized_content) < MIN_TEXT_CHARS:
        raise ValueError(f"Text content must be at least {MIN_TEXT_CHARS} characters")
    encoded = normalized_content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise ValueError("Text content exceeds 1 MB limit")
    if source_type not in {"txt", "transcript"}:
        raise ValueError("Text source type must be txt or transcript")
    capability = get_connector_capability(source_type)
    if not capability:
        raise ValueError("Text connector is not registered")
    _validate_collection(db, collection_id)

    filename = _safe_connector_filename(normalized_title, ".txt")
    metadata = {
        "inputConnector": source_type,
        "sourceKind": "text_paste" if source_type == "txt" else "transcript",
        "originalTitle": normalized_title,
        "charCountOriginal": len(normalized_content),
        "connector": {**(capability.__dict__), "lastError": None},
        "validation": {"maxBytes": MAX_TEXT_BYTES},
    }
    return create_source_record(
        db,
        filename=filename,
        mime_type="text/plain",
        file_size=len(encoded),
        file_bytes=encoded,
        collection_id=collection_id,
        actor=actor,
        source_type=source_type,
        metadata=metadata,
        description="Pasted text source is queued for processing.",
        title=normalized_title,
    )


def fetch_url_content(url: str) -> tuple[str, bytes, str, dict]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(json_dumps_error(connector_error("validation_error", "URL must be an absolute http(s) URL", "url")))

    request = urllib.request.Request(
        parsed.geturl(),
        headers={"User-Agent": "LLMWikiConnector/0.1 (+local-first-ingest)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = str(response.headers.get("Content-Type") or "text/html").split(";")[0].strip().lower()
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_CONNECTOR_BYTES:
                raise ValueError(json_dumps_error(connector_error("validation_error", "URL response exceeds 2 MB limit", "url")))
            body = response.read(MAX_CONNECTOR_BYTES + 1)
    except urllib.error.URLError as exc:
        raise ValueError(json_dumps_error(connector_error("fetch_error", f"Unable to fetch URL: {exc}", "url"))) from exc

    if len(body) > MAX_CONNECTOR_BYTES:
        raise ValueError(json_dumps_error(connector_error("validation_error", "URL response exceeds 2 MB limit", "url")))
    if content_type not in {"text/html", "application/xhtml+xml", "text/plain", "text/markdown"}:
        raise ValueError(json_dumps_error(connector_error("validation_error", f"Unsupported URL content type: {content_type}", "url")))

    decoded = body.decode("utf-8", errors="ignore")
    if content_type in {"text/html", "application/xhtml+xml"}:
        title, text = extract_readable_html(decoded)
    else:
        title, text = "", decoded
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ValueError(json_dumps_error(connector_error("parse_error", "URL did not contain enough readable text", "url")))
    capability = get_connector_capability("url")
    metadata = {
        "inputConnector": "url",
        "sourceKind": "web",
        "fetchedUrl": parsed.geturl(),
        "contentType": content_type,
        "rawBytes": len(body),
        "readableCharCount": len(text),
        "connector": {**(capability.__dict__ if capability else {}), "lastError": None},
        "validation": {"maxBytes": MAX_CONNECTOR_BYTES},
    }
    return title, text.encode("utf-8"), content_type, metadata


def json_dumps_error(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


def create_url_source_record(
    db: Session,
    *,
    url: str,
    title: str | None = None,
    collection_id: str | None = None,
    actor: str = "Current User",
) -> tuple[Source, Path]:
    _validate_collection(db, collection_id)
    extracted_title, file_bytes, content_type, metadata = fetch_url_content(url)
    resolved_title = " ".join((title or extracted_title or url).strip().split())
    filename = _safe_connector_filename(resolved_title, ".txt")
    return create_source_record(
        db,
        filename=filename,
        mime_type="text/plain",
        file_size=len(file_bytes),
        file_bytes=file_bytes,
        collection_id=collection_id,
        actor=actor,
        source_type="url",
        source_url=metadata["fetchedUrl"],
        metadata={**metadata, "originalTitle": resolved_title, "sourceContentType": content_type},
        description="Web URL source is queued for processing.",
        title=resolved_title,
    )


def refresh_url_source_record(db: Session, source_id: str, actor: str = "Current User") -> Source | None:
    source = db.query(Source).filter(Source.id == source_id, Source.source_type == "url").first()
    if not source or not source.url or not source.file_path:
        return None
    extracted_title, file_bytes, content_type, metadata = fetch_url_content(source.url)
    replace_source_bytes(source.file_path, file_bytes)
    source.title = source.title or extracted_title or source.url
    source.mime_type = "text/plain"
    source.file_size = len(file_bytes)
    source.checksum = hashlib.sha256(file_bytes).hexdigest()
    source.updated_at = datetime.now(timezone.utc)
    source.parse_status = "parsing"
    source.ingest_status = "parsing"
    source.metadata_json = {
        **(source.metadata_json or {}),
        **metadata,
        "refreshedBy": actor,
        "refreshedAt": source.updated_at.isoformat(),
        "sourceContentType": content_type,
    }
    db.commit()
    db.refresh(source)
    return source


def _reset_source_ingest_state(db: Session, source: Source) -> None:
    db.query(ExtractionRun).filter(ExtractionRun.source_id == source.id).delete(synchronize_session=False)
    db.query(KnowledgeUnit).filter(KnowledgeUnit.source_id == source.id).delete(synchronize_session=False)
    db.query(SourceSuggestion).filter(SourceSuggestion.source_id == source.id).delete(synchronize_session=False)
    db.query(SourceEntityLink).filter(SourceEntityLink.source_id == source.id).delete(synchronize_session=False)
    db.query(TimelineEvent).filter(TimelineEvent.source_id == source.id).delete(synchronize_session=False)
    db.query(GlossaryTerm).filter(GlossaryTerm.source_id == source.id).delete(synchronize_session=False)
    chunk_ids = [chunk_id for (chunk_id,) in db.query(SourceChunk.id).filter(SourceChunk.source_id == source.id).all()]
    if chunk_ids:
        db.query(ReviewIssue).filter(ReviewIssue.source_chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        db.query(Claim).filter(Claim.source_chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        db.query(SourceChunk).filter(SourceChunk.id.in_(chunk_ids)).delete(synchronize_session=False)

    page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id == source.id).all()]
    if page_ids:
        pages = db.query(Page).filter(Page.id.in_(page_ids)).all()
        for page in pages:
            review_items = db.query(ReviewItem).filter(ReviewItem.page_id == page.id).all()
            for review_item in review_items:
                db.query(ReviewIssue).filter(ReviewIssue.review_item_id == review_item.id).delete(synchronize_session=False)
                db.delete(review_item)

            linked_source_ids = [link.source_id for link in page.source_links]
            if page.owner == "Ingest Pipeline" and linked_source_ids == [source.id]:
                db.query(PageEntityLink).filter(PageEntityLink.page_id == page.id).delete(synchronize_session=False)
                db.delete(page)
            else:
                db.query(PageSourceLink).filter(
                    PageSourceLink.page_id == page.id,
                    PageSourceLink.source_id == source.id,
                ).delete(synchronize_session=False)

    preserved_metadata = {
        key: value
        for key, value in (source.metadata_json or {}).items()
        if key in {"inputConnector", "sourceKind", "originalTitle", "fetchedUrl", "contentType", "sourceContentType", "validation", "rawBytes", "readableCharCount", "charCountOriginal"}
    }
    source.metadata_json = preserved_metadata
    source.description = "Uploaded source is being processed."
    source.tags = []
    source.parse_status = "parsing"
    source.ingest_status = "parsing"
    source.updated_at = datetime.now(timezone.utc)
    assets_dir = ensure_upload_dir() / f"{Path(source.file_path).stem}-assets"
    if assets_dir.exists():
        shutil.rmtree(assets_dir, ignore_errors=True)
    db.flush()


def ingest_source(db: Session, source_id: str) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    timestamp = datetime.now(timezone.utc)
    try:
        connector_metadata = dict(source.metadata_json or {})
        load_runtime_snapshot(db)
        _reset_source_ingest_state(db, source)
        stored_path = Path(source.file_path)
        artifacts = run_ingest_pipeline(stored_path, source.mime_type, source.source_type, source.title)
        parsed = artifacts.parsed
        chunks = artifacts.chunks
        summary = artifacts.summary
        key_facts = artifacts.key_facts
        tags = artifacts.tags
        generated_entities = artifacts.entities
        generated_claims = artifacts.claims
        timeline_events = artifacts.timeline_events
        glossary_terms = artifacts.glossary_terms
        page_type_candidates = artifacts.page_type_candidates
        runtime = load_runtime_snapshot(db)
        embedding_profile = runtime.profile_for_task("embeddings")
        ingest_profile = runtime.profile_for_task("ingest_summary")
        claim_profile = runtime.profile_for_task("claim_extraction")
        entity_profile = runtime.profile_for_task("entity_glossary_timeline")
        chunk_embeddings = embedding_client.embed_texts(embedding_profile, [chunk["content"] for chunk in chunks]) if chunks else None

        source.metadata_json = {
            **connector_metadata,
            **parsed.metadata,
            "charCount": len(parsed.text),
            "chunkCount": len(chunks),
            "pipelineStages": serialize_stage_results(artifacts.stage_results),
            "pageTypeCandidates": page_type_candidates,
            "timelineEvents": timeline_events,
            "glossaryTerms": glossary_terms,
            "generation": prompt_metadata("ingest_summary", ingest_profile.provider, ingest_profile.model),
        }
        source.description = summary
        source.tags = tags
        if source.collection_id is None:
            suggested_collection_id = _suggest_collection(db, source.title, tags)
            source.metadata_json = {**source.metadata_json, "suggestedCollectionId": suggested_collection_id}
        else:
            source.metadata_json = {**source.metadata_json, "suggestedCollectionId": source.collection_id}
        source.parse_status = "chunked" if chunks else "parsed"
        source.ingest_status = source.parse_status

        entity_id_map: dict[str, str] = {}
        for entity in generated_entities:
            existing = db.query(Entity).filter(Entity.normalized_name == entity["normalized_name"]).first()
            if existing:
                entity_id_map[entity["name"]] = existing.id
                db.add(
                    SourceEntityLink(
                        id=f"sel-{uuid4().hex[:8]}",
                        source_id=source.id,
                        entity_id=existing.id,
                        mention_count=int(entity.get("mention_count") or 1),
                        confidence_score=float(entity.get("confidence_score") or 0.7),
                    )
                )
                continue
            record = Entity(
                id=entity["id"],
                name=entity["name"],
                entity_type=entity["entity_type"],
                description=entity["description"],
                aliases=entity["aliases"],
                normalized_name=entity["normalized_name"],
                created_at=timestamp,
            )
            db.add(record)
            db.flush()
            entity_id_map[entity["name"]] = record.id
            db.add(
                SourceEntityLink(
                    id=f"sel-{uuid4().hex[:8]}",
                    source_id=source.id,
                    entity_id=record.id,
                    mention_count=int(entity.get("mention_count") or 1),
                    confidence_score=float(entity.get("confidence_score") or 0.7),
                )
            )

        chunk_records: list[SourceChunk] = []
        for index, chunk in enumerate(chunks):
            embedding_vector = chunk_embeddings[index] if chunk_embeddings and index < len(chunk_embeddings) else []
            chunk_metadata = dict(chunk.get("metadata") or {})
            record = SourceChunk(
                id=f"chunk-{uuid4().hex[:8]}",
                source_id=source.id,
                chunk_index=index,
                section_title=chunk["section_title"],
                page_number=chunk_metadata.get("pageNumber") or index + 1,
                content=chunk["content"],
                token_count=chunk["token_count"],
                embedding_id=f"emb-{uuid4().hex[:8]}" if embedding_vector else None,
                metadata_json={
                    **chunk_metadata,
                    "embedding": embedding_vector,
                    "embeddingModel": embedding_profile.model if embedding_vector else None,
                    "embeddingProvider": embedding_profile.provider if embedding_vector else None,
                },
                span_start=0,
                span_end=len(chunk["content"]),
                created_at=timestamp,
            )
            db.add(record)
            db.flush()
            chunk_records.append(record)

        claim_records: list[tuple[Claim, SourceChunk]] = []
        for claim_payload in generated_claims:
            chunk_index = int(claim_payload.get("chunk_index") or 0)
            chunk_record = chunk_records[min(chunk_index, max(len(chunk_records) - 1, 0))] if chunk_records else None
            if chunk_record is None:
                continue
            claim = Claim(
                id=claim_payload["id"],
                source_chunk_id=chunk_record.id,
                text=claim_payload["text"],
                claim_type=claim_payload["claim_type"],
                confidence_score=claim_payload["confidence_score"],
                canonical_status=claim_payload["canonical_status"],
                review_status=claim_payload["review_status"],
                extracted_at=timestamp,
                topic=claim_payload["topic"],
                entity_ids=claim_payload["entity_ids"],
                extraction_method=claim_payload.get("extraction_method") or "heuristic",
                evidence_span_start=claim_payload.get("evidence_span_start"),
                evidence_span_end=claim_payload.get("evidence_span_end"),
                metadata_json=claim_payload.get("metadata_json") or {},
            )
            db.add(claim)
            claim_records.append((claim, chunk_record))

        knowledge_unit_records: list[KnowledgeUnit] = []
        for claim, chunk_record in claim_records:
            metadata_json = dict(claim.metadata_json or {})
            metadata_json.setdefault("sourceChunkIndex", chunk_record.chunk_index)
            metadata_json.setdefault("sourceChunkSectionTitle", chunk_record.section_title)
            metadata_json.setdefault("origin", "claim_extraction")
            unit = KnowledgeUnit(
                id=f"ku-{uuid4().hex[:8]}",
                source_id=source.id,
                source_chunk_id=chunk_record.id,
                claim_id=claim.id,
                unit_type=claim.claim_type,
                title=(claim.topic or claim.claim_type.replace("_", " ").title())[:255],
                text=claim.text,
                status="candidate" if metadata_json.get("isLowConfidence") else "draft",
                review_status=claim.review_status,
                canonical_status="candidate" if claim.canonical_status == "unverified" else claim.canonical_status,
                confidence_score=claim.confidence_score,
                topic=claim.topic,
                entity_ids=claim.entity_ids or [],
                evidence_span_start=claim.evidence_span_start,
                evidence_span_end=claim.evidence_span_end,
                metadata_json=metadata_json,
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(unit)
            knowledge_unit_records.append(unit)

        _create_extraction_run(
            db,
            source_id=source.id,
            run_type="claim_extraction",
            status="completed",
            method=_derive_claim_run_method(generated_claims),
            task_profile="claim_extraction",
            model_provider=claim_profile.provider,
            model_name=claim_profile.model,
            input_chunk_count=len(chunks),
            output_count=len(knowledge_unit_records),
            metadata_json={
                "claimCount": len(generated_claims),
                "knowledgeUnitCount": len(knowledge_unit_records),
                "lowConfidenceCount": sum(1 for claim, _chunk in claim_records if claim.confidence_score < 0.62 or (claim.metadata_json or {}).get("isLowConfidence")),
            },
            started_at=timestamp,
            finished_at=datetime.now(timezone.utc),
        )

        _create_extraction_run(
            db,
            source_id=source.id,
            run_type="entity_extraction",
            status="completed",
            method="heuristic",
            task_profile="entity_glossary_timeline",
            model_provider=entity_profile.provider,
            model_name=entity_profile.model,
            input_chunk_count=len(chunks),
            output_count=len(generated_entities),
            metadata_json={"entityCount": len(generated_entities)},
            started_at=timestamp,
            finished_at=datetime.now(timezone.utc),
        )
        _create_extraction_run(
            db,
            source_id=source.id,
            run_type="timeline_extraction",
            status="completed",
            method="heuristic",
            task_profile="entity_glossary_timeline",
            model_provider=entity_profile.provider,
            model_name=entity_profile.model,
            input_chunk_count=len(chunks),
            output_count=len(timeline_events),
            metadata_json={"eventCount": len(timeline_events)},
            started_at=timestamp,
            finished_at=datetime.now(timezone.utc),
        )
        _create_extraction_run(
            db,
            source_id=source.id,
            run_type="glossary_extraction",
            status="completed",
            method="heuristic",
            task_profile="entity_glossary_timeline",
            model_provider=entity_profile.provider,
            model_name=entity_profile.model,
            input_chunk_count=len(chunks),
            output_count=len(glossary_terms),
            metadata_json={"termCount": len(glossary_terms)},
            started_at=timestamp,
            finished_at=datetime.now(timezone.utc),
        )

        source.parse_status = "indexed"
        source.ingest_status = "indexed"
        source.updated_at = datetime.now(timezone.utc)

        page_slug = slugify(Path(source.title).stem) or f"source-{source.id}"
        if db.query(Page).filter(Page.slug == page_slug).first():
            page_slug = f"{page_slug}-{source.id[-4:]}"
        primary_page_type = _primary_page_type(page_type_candidates)
        page_suggestions = _rank_page_suggestions(db, Path(source.title).stem.replace("-", " ").title(), summary, tags, exclude_slug=page_slug)
        citation_markers = [f" [^{index}]" for index in range(1, min(len(key_facts), len(claim_records)) + 1)]
        citation_notes = [
            f"[^{index}]: {source.title}, chunk {chunk.chunk_index + 1}. {claim.text[:180]}"
            for index, (claim, chunk) in enumerate(claim_records[: max(len(citation_markers), 5)], start=1)
        ]
        page = create_page_with_version(
            db,
            title=Path(source.title).stem.replace("-", " ").title(),
            slug=page_slug,
            summary=summary,
            content_md=build_page_markdown(
                Path(source.title).stem.replace("-", " ").title(),
                summary,
                chunks,
                key_facts,
                page_type=primary_page_type,
                entities=generated_entities,
                timeline_events=timeline_events,
                glossary_terms=glossary_terms,
                image_urls=list(parsed.metadata.get("images", [])),
                ordered_blocks=list(parsed.metadata.get("orderedBlocks", [])),
                citation_markers=citation_markers,
                citation_notes=citation_notes,
            ),
            owner="Ingest Pipeline",
            page_type=primary_page_type,
            status="in_review",
            tags=tags,
            key_facts=key_facts,
            related_source_ids=[source.id],
            related_entity_ids=list(entity_id_map.values()),
            collection_id=source.collection_id,
        )

        for index, (claim, _) in enumerate(claim_records[:8], start=1):
            db.add(
                PageClaimLink(
                    id=f"pcl-{uuid4().hex[:8]}",
                    page_id=page.id,
                    claim_id=claim.id,
                    section_key="key_facts" if index <= len(key_facts) else "source_walkthrough",
                    citation_style="footnote",
                )
            )

        if suggested_collection_id := source.metadata_json.get("suggestedCollectionId"):
            collection = db.query(Collection).filter(Collection.id == suggested_collection_id).first()
            if collection and source.collection_id != collection.id:
                create_source_suggestion(
                    db,
                    source_id=source.id,
                    suggestion_type="collection_match",
                    target_type="collection",
                    target_id=collection.id,
                    target_label=collection.name,
                    confidence_score=0.78,
                    reason="Collection matched by source title, summary, and extracted tags.",
                    evidence=[{"tags": tags[:6], "summary": summary[:220]}],
                )

        for matched_page, confidence, matches in page_suggestions:
            create_source_suggestion(
                db,
                source_id=source.id,
                suggestion_type="page_match",
                target_type="page",
                target_id=matched_page.id,
                target_label=matched_page.title,
                confidence_score=confidence,
                reason="Existing page shares high-signal title, summary, or tag terms with this source.",
                evidence=[{"matchedTerms": matches, "pageSlug": matched_page.slug}],
            )

        for entity_name, entity_id in list(entity_id_map.items())[:5]:
            create_source_suggestion(
                db,
                source_id=source.id,
                suggestion_type="entity_match",
                target_type="entity",
                target_id=entity_id,
                target_label=entity_name,
                confidence_score=0.72,
                reason="Entity was extracted from the source and matched or created in the entity index.",
                evidence=[{"entityName": entity_name}],
                status="accepted",
            )

        create_source_suggestion(
            db,
            source_id=source.id,
            suggestion_type="new_page",
            target_type="page",
            target_id=page.id,
            target_label=page.title,
            confidence_score=0.82,
            reason="A new source-derived page was generated for reviewer approval.",
            evidence=[{"pageSlug": page.slug, "pageType": page.page_type}],
            status="accepted",
        )

        auxiliary_pages: list[Page] = []
        if generated_entities:
            entity = generated_entities[0]
            entity_title = entity["name"]
            auxiliary_pages.append(
                create_page_with_version(
                    db,
                    title=entity_title,
                    slug=_unique_page_slug(db, entity_title),
                    summary=entity["description"],
                    content_md=build_page_markdown(
                        entity_title,
                        entity["description"],
                        chunks[:2],
                        [entity["description"]],
                        page_type="entity",
                        entities=generated_entities,
                        citation_notes=citation_notes[:3],
                    ),
                    owner="Ingest Pipeline",
                    page_type="entity",
                    status="draft",
                    tags=sorted(set([*tags[:4], "entity"])),
                    key_facts=[entity["description"]],
                    related_source_ids=[source.id],
                    related_entity_ids=[entity_id_map.get(entity["name"], entity["id"])],
                    collection_id=source.collection_id,
                )
            )

        if timeline_events:
            timeline_title = f"{Path(source.title).stem.replace('-', ' ').title()} Timeline"
            auxiliary_pages.append(
                create_page_with_version(
                    db,
                    title=timeline_title,
                    slug=_unique_page_slug(db, timeline_title),
                    summary=f"Timeline extracted from {source.title} with {len(timeline_events)} dated events.",
                    content_md=build_page_markdown(
                        timeline_title,
                        f"Timeline extracted from {source.title} with {len(timeline_events)} dated events.",
                        chunks[:2],
                        [event["title"] for event in timeline_events[:4]],
                        page_type="timeline",
                        timeline_events=timeline_events,
                        citation_notes=citation_notes[:3],
                    ),
                    owner="Ingest Pipeline",
                    page_type="timeline",
                    status="draft",
                    tags=sorted(set([*tags[:4], "timeline"])),
                    key_facts=[event["title"] for event in timeline_events[:4]],
                    related_source_ids=[source.id],
                    related_entity_ids=list(entity_id_map.values()),
                    collection_id=source.collection_id,
                )
            )

        if glossary_terms:
            glossary_title = f"{Path(source.title).stem.replace('-', ' ').title()} Glossary"
            auxiliary_pages.append(
                create_page_with_version(
                    db,
                    title=glossary_title,
                    slug=_unique_page_slug(db, glossary_title),
                    summary=f"Glossary extracted from {source.title} with {len(glossary_terms)} terms.",
                    content_md=build_page_markdown(
                        glossary_title,
                        f"Glossary extracted from {source.title} with {len(glossary_terms)} terms.",
                        chunks[:2],
                        [f"{term['term']}: {term['definition']}" for term in glossary_terms[:4]],
                        page_type="glossary",
                        glossary_terms=glossary_terms,
                        citation_notes=citation_notes[:3],
                    ),
                    owner="Ingest Pipeline",
                    page_type="glossary",
                    status="draft",
                    tags=sorted(set([*tags[:4], "glossary"])),
                    key_facts=[f"{term['term']}: {term['definition']}" for term in glossary_terms[:4]],
                    related_source_ids=[source.id],
                    related_entity_ids=list(entity_id_map.values()),
                    collection_id=source.collection_id,
                )
            )

        for auxiliary_page in auxiliary_pages:
            page.related_page_ids = sorted(set([*(page.related_page_ids or []), auxiliary_page.id]))
            auxiliary_page.related_page_ids = sorted(set([page.id]))
            create_source_suggestion(
                db,
                source_id=source.id,
                suggestion_type="new_page",
                target_type="page",
                target_id=auxiliary_page.id,
                target_label=auxiliary_page.title,
                confidence_score=0.74,
                reason=f"Generated structured {auxiliary_page.page_type} page from extracted source data.",
                evidence=[{"pageSlug": auxiliary_page.slug, "pageType": auxiliary_page.page_type}],
                status="accepted",
            )

        for entity_id in entity_id_map.values():
            db.add(
                PageEntityLink(
                    id=f"pel-{uuid4().hex[:8]}",
                    page_id=page.id,
                    entity_id=entity_id,
                    relation_type="derived_from_source",
                    confidence_score=0.82,
                )
            )

        for event in timeline_events:
            db.add(
                TimelineEvent(
                    id=event["id"],
                    source_id=source.id,
                    page_id=page.id,
                    event_date=event["event_date"],
                    sort_key=event["sort_key"],
                    title=event["title"],
                    description=event["description"],
                    precision=event["precision"],
                    entity_ids=[entity_id for entity_id in event.get("entity_ids", []) if entity_id],
                )
            )
            create_source_suggestion(
                db,
                source_id=source.id,
                suggestion_type="timeline_match",
                target_type="timeline",
                target_id=event["id"],
                target_label=event["title"],
                confidence_score=0.7,
                reason="Timeline event was extracted from dated source evidence.",
                evidence=[{"eventDate": event["event_date"], "precision": event["precision"]}],
                status="accepted",
            )

        for term in glossary_terms:
            db.add(
                GlossaryTerm(
                    id=term["id"],
                    source_id=source.id,
                    page_id=page.id,
                    term=term["term"],
                    normalized_term=term["normalized_term"],
                    definition=term["definition"],
                    aliases=term.get("aliases", []),
                    confidence_score=float(term.get("confidence_score") or 0.7),
                )
            )

        low_confidence_claims = [claim for claim, _chunk in claim_records if claim.confidence_score < 0.62 or (claim.metadata_json or {}).get("isLowConfidence")]
        review_issue_type = "low_confidence" if low_confidence_claims else ("missing_citation" if len(chunks) < 2 else "unsupported_claim")
        review_severity = "high" if low_confidence_claims or len(chunks) < 2 else "medium"
        review_item = ReviewItem(
            id=f"rev-{uuid4().hex[:8]}",
            page_id=page.id,
            page_title=page.title,
            page_slug=page.slug,
            page_status=page.status,
            issue_type=review_issue_type,
            severity=review_severity,
            old_content_md="",
            new_content_md=page.content_md,
            change_summary="Auto-generated from uploaded source and awaiting review",
            confidence_score=runtime.auto_review_threshold,
            created_at=timestamp,
            updated_at=timestamp,
            assigned_to=None,
            previous_version=None,
            source_ids=[source.id],
            evidence_snippets=[
                {
                    "sourceId": source.id,
                    "sourceTitle": source.title,
                    "chunkId": (claim_records[0][1].id if low_confidence_claims and claim_records else chunk_records[0].id if chunk_records else None),
                    "content": (
                        low_confidence_claims[0].text[:260]
                        if low_confidence_claims
                        else chunk_records[0].content[:260] if chunk_records else summary[:260]
                    ),
                    "relevance": 0.87,
                }
            ],
        )
        db.add(review_item)
        db.flush()
        db.add(
            ReviewIssue(
                id=f"ri-{uuid4().hex[:8]}",
                review_item_id=review_item.id,
                issue_type=review_item.issue_type,
                severity=review_item.severity,
                message="Auto-generated page requires reviewer approval before publication." if not low_confidence_claims else "At least one extracted claim is low-confidence and should be checked before publication.",
                evidence="The page was created from upload ingestion and should be checked for accuracy and citations." if not low_confidence_claims else f"Low-confidence claim count: {len(low_confidence_claims)}",
                source_chunk_id=(claim_records[0][1].id if low_confidence_claims and claim_records else chunk_records[0].id if chunk_records else None),
                claim_id=(low_confidence_claims[0].id if low_confidence_claims else None),
            )
        )

        db.commit()
        db.refresh(source)
    except Exception as exc:
        db.rollback()
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return None
        failure_time = datetime.now(timezone.utc)
        db.add(
            ExtractionRun(
                id=f"er-{uuid4().hex[:8]}",
                source_id=source.id,
                run_type="ingest_pipeline",
                status="failed",
                method="system",
                task_profile="",
                model_provider="none",
                model_name="",
                prompt_version=PROMPT_VERSION,
                input_chunk_count=0,
                output_count=0,
                error_message=str(exc),
                metadata_json={"sourceType": source.source_type, "mimeType": source.mime_type},
                started_at=timestamp,
                finished_at=failure_time,
            )
        )
        source.parse_status = "failed"
        source.ingest_status = "failed"
        source.description = f"Processing failed: {exc}"
        source.updated_at = failure_time
        db.add(source)
        db.commit()
        db.refresh(source)

    return _serialize_source(source)


def create_uploaded_source(db: Session, filename: str, mime_type: str, file_size: int | None, file_bytes: bytes, actor: str = "Current User") -> dict:
    source, _ = create_source_record(db, filename, mime_type, file_size, file_bytes, actor=actor)
    return _serialize_source(source)
