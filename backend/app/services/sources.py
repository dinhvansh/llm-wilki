from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import mimetypes
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.request
from urllib.parse import unquote, urlparse
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
    public_upload_url,
    run_ingest_pipeline,
    serialize_stage_results,
    slugify,
)
from app.core.llm_client import llm_client
from app.core.reliability import PROMPT_VERSION
from app.core.runtime_config import load_runtime_snapshot
from app.core.storage import read_object_bytes, refresh_object_bytes, save_existing_file_object, save_source_object, StorageError
from app.models import Claim, Collection, Entity, ExtractionRun, GlossaryTerm, KnowledgeUnit, Page, PageClaimLink, PageEntityLink, PageSourceLink, Source, SourceArtifactRecord, SourceChunk, SourceEntityLink, SourceSuggestion, StorageObject, TimelineEvent
from app.models import ReviewIssue, ReviewItem
from app.services.pages import create_page_with_version
from app.services.permissions import apply_collection_scope_filter, can_access_collection_id
from app.services.suggestions import create_source_suggestion


ALLOWED_PAGE_TYPES = {"summary", "overview", "deep_dive", "entity", "source_derived", "faq", "glossary", "timeline", "sop", "concept", "issue"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_CONNECTOR_BYTES = 2 * 1024 * 1024
MAX_TEXT_BYTES = 1024 * 1024
MIN_TEXT_CHARS = 20
SOURCE_TRUST_LEVELS = {"high", "medium", "low"}
SOURCE_STATUS_VALUES = {"draft", "approved", "archived", "superseded"}
AUTHORITY_LEVEL_VALUES = {"official", "reference", "informal"}
KNOWLEDGE_UNIT_TYPES = {"definition", "rule", "procedure_step", "condition", "exception", "threshold", "warning", "decision", "relationship", "example", "fact"}


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


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text or None


def _source_metadata_fields(source: Source) -> dict:
    metadata = source.metadata_json or {}
    return {
        "documentType": _string_or_none(metadata.get("documentType") or metadata.get("document_type")),
        "sourceStatus": _string_or_none(metadata.get("sourceStatus") or metadata.get("source_status")),
        "authorityLevel": _string_or_none(metadata.get("authorityLevel") or metadata.get("authority_level")),
        "effectiveDate": _string_or_none(metadata.get("effectiveDate") or metadata.get("effective_date")),
        "version": _string_or_none(metadata.get("version")),
        "owner": _string_or_none(metadata.get("owner")),
    }


def _normalize_knowledge_unit_type(claim: Claim, metadata: dict | None = None) -> str:
    metadata = metadata or {}
    claim_type = str(claim.claim_type or "").lower()
    text = f"{claim.text or ''}\n{claim.topic or ''}".lower()
    section_role = str(metadata.get("sectionRole") or "").lower()

    if claim_type == "definition":
        return "definition"
    if claim_type in {"rule", "requirement"}:
        if re.search(r"\bthreshold\b|\blimit\b|\bsla\b|\btarget\b|\babove\b|\bbelow\b|\bmore than\b|\bless than\b", text):
            return "threshold"
        if section_role == "exception":
            return "exception"
        return "rule"
    if claim_type in {"process", "instruction"}:
        return "procedure_step"
    if claim_type == "condition":
        return "condition"
    if claim_type == "decision":
        return "decision"
    if claim_type == "example":
        return "example"
    if claim_type == "risk":
        return "warning"
    if claim_type == "metric":
        return "threshold"
    if claim_type == "fact" and len(claim.entity_ids or []) >= 2:
        return "relationship"
    return claim_type if claim_type in KNOWLEDGE_UNIT_TYPES else "fact"


def _unique_note_texts(values: list[str], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _build_notebook_context(
    source: Source,
    summary: str,
    key_facts: list[str],
    section_summaries: list[dict],
    source_sections: list[dict],
    claim_records: list[tuple[Claim, SourceChunk]],
    knowledge_unit_records: list[KnowledgeUnit],
) -> dict:
    source_metadata = source.metadata_json or {}
    source_brief = summary.strip() or source.description or source.title
    key_points = _unique_note_texts(key_facts or [source_brief], limit=6)
    section_by_key = {
        str(section.get("sectionKey") or ""): section
        for section in source_sections
        if str(section.get("sectionKey") or "").strip()
    }
    chunk_lookup = {chunk.id: chunk for _claim, chunk in claim_records}
    claim_lookup = {claim.id: claim for claim, _chunk in claim_records}
    grouped: dict[str, dict] = {
        "procedures": {"title": "Procedures", "role": "step", "items": [], "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
        "rules": {"title": "Rules And Thresholds", "role": "evidence", "items": [], "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
        "risks": {"title": "Risks And Caveats", "role": "exception", "items": [], "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
        "decisions": {"title": "Decisions And Judgement Calls", "role": "detail", "items": [], "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
    }

    def _assign_group(unit_type: str, section_role: str | None) -> str:
        lowered_type = str(unit_type or "").lower()
        lowered_role = str(section_role or "").lower()
        if lowered_type in {"procedure_step", "condition"} or lowered_role in {"step", "prerequisite"}:
            return "procedures"
        if lowered_type in {"exception", "warning"} or lowered_role in {"exception", "risk"}:
            return "risks"
        if lowered_type in {"decision", "relationship", "example"}:
            return "decisions"
        return "rules"

    for unit in knowledge_unit_records:
        metadata = unit.metadata_json or {}
        chunk_id = unit.source_chunk_id or metadata.get("sourceChunkId")
        claim_id = unit.claim_id
        section_key = metadata.get("parentSectionKey")
        bucket = grouped[_assign_group(unit.unit_type, metadata.get("sectionRole"))]
        bucket["items"].append(unit.text)
        if chunk_id:
            bucket["chunkIds"].append(str(chunk_id))
        if claim_id:
            bucket["claimIds"].append(str(claim_id))
        bucket["unitIds"].append(unit.id)
        if section_key:
            bucket["sectionKeys"].append(str(section_key))

    if not any(bucket["items"] for bucket in grouped.values()):
        for claim, chunk in claim_records:
            metadata = claim.metadata_json or {}
            bucket = grouped[_assign_group(claim.claim_type, metadata.get("sectionRole"))]
            bucket["items"].append(claim.text)
            bucket["chunkIds"].append(chunk.id)
            bucket["claimIds"].append(claim.id)
            if metadata.get("parentSectionKey"):
                bucket["sectionKeys"].append(str(metadata["parentSectionKey"]))

    notes: list[dict] = [
        {
            "id": "source-brief",
            "kind": "source_brief",
            "title": "Source Brief",
            "text": source_brief,
            "roles": ["summary"],
            "provenance": {"sourceId": source.id, "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
        }
    ]
    for index, point in enumerate(key_points, start=1):
        notes.append(
            {
                "id": f"key-point-{index}",
                "kind": "key_point",
                "title": f"Key Point {index}",
                "text": point,
                "roles": ["summary", "evidence"],
                "provenance": {"sourceId": source.id, "chunkIds": [], "claimIds": [], "unitIds": [], "sectionKeys": []},
            }
        )

    for key, payload in grouped.items():
        items = _unique_note_texts(payload["items"], limit=4)
        if not items:
            continue
        notes.append(
            {
                "id": key,
                "kind": "grouped_note",
                "title": payload["title"],
                "text": "\n".join(f"- {item}" for item in items),
                "roles": [payload["role"]],
                "provenance": {
                    "sourceId": source.id,
                    "chunkIds": _unique_note_texts(payload["chunkIds"], limit=8),
                    "claimIds": _unique_note_texts(payload["claimIds"], limit=8),
                    "unitIds": _unique_note_texts(payload["unitIds"], limit=8),
                    "sectionKeys": _unique_note_texts(payload["sectionKeys"], limit=8),
                },
            }
        )

    recommended_prompts = _unique_note_texts(
        [
            f"Summarize {source.title}.",
            f"What should I read first in {source.title}?",
            f"What procedures or steps matter most in {source.title}?" if grouped["procedures"]["items"] else "",
            f"What rules or thresholds matter most in {source.title}?" if grouped["rules"]["items"] else "",
            f"What risks or caveats appear in {source.title}?" if grouped["risks"]["items"] else "",
            f"What decisions or judgement calls appear in {source.title}?" if grouped["decisions"]["items"] else "",
        ],
        limit=6,
    )

    return {
        "sourceBrief": source_brief,
        "keyPoints": key_points,
        "notes": notes,
        "recommendedPrompts": recommended_prompts,
        "sectionCount": len(section_summaries),
        "sectionKeys": [str(section.get("sectionKey") or "") for section in section_summaries[:12]],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "documentType": _string_or_none(source_metadata.get("documentType") or source_metadata.get("document_type")),
    }


def _serialize_source(source: Source) -> dict:
    metadata_fields = _source_metadata_fields(source)
    storage_objects = [
        {
            "id": item.id,
            "backend": item.backend,
            "bucket": item.bucket,
            "objectKey": item.object_key,
            "localPath": item.local_path,
            "originalFilename": item.original_filename,
            "contentType": item.content_type,
            "byteSize": item.byte_size,
            "checksumSha256": item.checksum_sha256,
            "lifecycleState": item.lifecycle_state,
            "createdAt": _iso(item.created_at),
        }
        for item in sorted(source.storage_objects or [], key=lambda object_: object_.created_at, reverse=True)
    ]
    return {
        "id": source.id,
        "title": source.title,
        "sourceType": source.source_type,
        "documentType": metadata_fields["documentType"],
        "mimeType": source.mime_type,
        "filePath": source.file_path,
        "url": source.url,
        "uploadedAt": _iso(source.uploaded_at),
        "updatedAt": _iso(source.updated_at),
        "createdBy": source.created_by,
        "parseStatus": source.parse_status,
        "ingestStatus": source.ingest_status,
        "metadataJson": {**(source.metadata_json or {}), "storageObjects": storage_objects},
        "checksum": source.checksum,
        "trustLevel": source.trust_level,
        "fileSize": source.file_size,
        "description": source.description,
        "tags": source.tags or [],
        "collectionId": source.collection_id,
        "sourceStatus": metadata_fields["sourceStatus"],
        "authorityLevel": metadata_fields["authorityLevel"],
        "effectiveDate": metadata_fields["effectiveDate"],
        "version": metadata_fields["version"],
        "owner": metadata_fields["owner"],
    }


def _paginate(items: list[dict], page: int, page_size: int) -> dict:
    start = (page - 1) * page_size
    data = items[start : start + page_size]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def list_sources(db: Session, page: int = 1, page_size: int = 20, status: str | None = None, source_type: str | None = None, search: str | None = None, collection_id: str | None = None, actor=None) -> dict:
    query = db.query(Source)
    if actor is not None:
        query = apply_collection_scope_filter(query, Source, actor)
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


def get_source_by_id(db: Session, source_id: str, actor=None) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if source and actor is not None and not can_access_collection_id(actor, source.collection_id):
        return None
    return _serialize_source(source) if source else None


def list_source_storage_objects(db: Session, source_id: str, actor=None) -> list[dict] | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source or (actor is not None and not can_access_collection_id(actor, source.collection_id)):
        return None
    rows = (
        db.query(StorageObject)
        .filter(StorageObject.source_id == source_id)
        .order_by(StorageObject.created_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "backend": row.backend,
            "bucket": row.bucket,
            "objectKey": row.object_key,
            "localPath": row.local_path,
            "originalFilename": row.original_filename,
            "contentType": row.content_type,
            "byteSize": row.byte_size,
            "checksumSha256": row.checksum_sha256,
            "lifecycleState": row.lifecycle_state,
            "owner": row.owner,
            "sourceId": row.source_id,
            "artifactId": row.artifact_id,
            "metadataJson": row.metadata_json or {},
            "createdAt": _iso(row.created_at),
            "updatedAt": _iso(row.updated_at),
        }
        for row in rows
    ]


def get_storage_object_download(db: Session, object_id: str, actor=None) -> tuple[StorageObject, bytes] | None:
    row = db.query(StorageObject).filter(StorageObject.id == object_id, StorageObject.lifecycle_state == "active").first()
    if not row:
        return None
    if row.source_id:
        source = db.query(Source).filter(Source.id == row.source_id).first()
        if source and actor is not None and not can_access_collection_id(actor, source.collection_id):
            return None
    payload = read_object_bytes(row.backend, row.object_key, local_path=row.local_path, bucket=row.bucket)
    return row, payload


def _clean_preview_text(value: object, limit: int = 600) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return None
    return text[:limit]


def _resolve_public_upload_path(url: str | None) -> Path | None:
    if not url:
        return None
    normalized = str(url).strip()
    prefix = "/backend-uploads/"
    if not normalized.startswith(prefix):
        return None
    relative = unquote(normalized[len(prefix) :]).strip("/")
    if not relative:
        return None
    candidate = (ensure_upload_dir() / relative).resolve()
    root = ensure_upload_dir().resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def _fallback_image_caption(source: Source, *, context_before: str | None, alt_text: str | None, filename: str | None) -> tuple[str, str]:
    context = _clean_preview_text(context_before, limit=260)
    alt = _clean_preview_text(alt_text, limit=180)
    if context and alt:
        return (f"Image related to `{source.title}`. Context: {context}", alt)
    if context:
        return (f"Image related to `{source.title}`. Context: {context}", context)
    if alt:
        return (f"Image artifact referenced in `{source.title}`.", alt)
    filename_text = _clean_preview_text(filename, limit=120)
    return ("Image artifact extracted from source for multimodal review.", filename_text or source.title)


def _caption_image_with_context(source: Source, image_path: Path | None, *, context_before: str | None, alt_text: str | None) -> tuple[str, str | None, str]:
    fallback_summary, fallback_preview = _fallback_image_caption(
        source,
        context_before=context_before,
        alt_text=alt_text,
        filename=image_path.name if image_path else None,
    )
    if image_path is None or not image_path.exists():
        return fallback_summary, fallback_preview, "contextual_fallback"

    runtime = load_runtime_snapshot()
    profile = runtime.profile_for_task("ingest_summary")
    mime_type = mimetypes.guess_type(image_path.name)[0] or infer_mime_type(image_path.name, None) or "image/png"
    if not llm_client.is_enabled(profile):
        return fallback_summary, fallback_preview, "contextual_fallback"

    try:
        image_bytes = image_path.read_bytes()
    except OSError:
        return fallback_summary, fallback_preview, "contextual_fallback"

    system_prompt = (
        "You inspect document images for an internal knowledge base ingest pipeline. "
        "Return strict JSON with keys summary and preview_text. "
        "summary must describe the visual in one sentence tied to the surrounding document context. "
        "preview_text should be a short label or notable detail, max 18 words."
    )
    user_prompt = (
        f"Source title: {source.title}\n"
        f"Source type: {source.source_type}\n"
        f"Nearby document context: {context_before or 'None'}\n"
        f"Existing alt text: {alt_text or 'None'}\n"
        "Describe the image in a grounded, concise way for later retrieval."
    )
    response = llm_client.complete_with_image(
        profile,
        system_prompt,
        user_prompt,
        image_bytes=image_bytes,
        mime_type=mime_type,
    )
    if not response:
        return fallback_summary, fallback_preview, "contextual_fallback"
    try:
        from app.core.ingest import json_like_to_dict

        payload = json_like_to_dict(response)
        summary = _clean_preview_text(payload.get("summary"), limit=280) or fallback_summary
        preview = _clean_preview_text(payload.get("preview_text"), limit=180) or fallback_preview
        return summary, preview, "vision_model"
    except Exception:
        return fallback_summary, fallback_preview, "contextual_fallback"


def _persist_source_artifacts(db: Session, source: Source, artifacts: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    old_artifact_ids = [row_id for (row_id,) in db.query(SourceArtifactRecord.id).filter(SourceArtifactRecord.source_id == source.id).all()]
    if old_artifact_ids:
        db.query(StorageObject).filter(StorageObject.artifact_id.in_(old_artifact_ids)).update(
            {
                StorageObject.artifact_id: None,
                StorageObject.lifecycle_state: "orphaned",
                StorageObject.updated_at: now,
            },
            synchronize_session=False,
        )
    db.query(SourceArtifactRecord).filter(SourceArtifactRecord.source_id == source.id).delete()
    for item in artifacts:
        artifact_id = str(item.get("id") or f"{source.id}-artifact-{uuid4().hex[:8]}")
        metadata_json = item.get("metadataJson") if isinstance(item.get("metadataJson"), dict) else {}
        artifact = SourceArtifactRecord(
            id=artifact_id,
            source_id=source.id,
            artifact_type=str(item.get("artifactType") or "unknown"),
            title=str(item.get("title") or "Untitled artifact"),
            status=str(item.get("status") or "available"),
            content_type=_string_or_none(item.get("contentType")),
            summary=_string_or_none(item.get("summary")),
            preview_text=_string_or_none(item.get("previewText")),
            url=_string_or_none(item.get("url")),
            page_number=int(item["pageNumber"]) if item.get("pageNumber") is not None else None,
            metadata_json=metadata_json,
            created_at=now,
            updated_at=now,
        )
        db.add(artifact)
        artifact_path = _resolve_public_upload_path(artifact.url)
        if not artifact_path:
            continue
        try:
            stored_object = save_existing_file_object(artifact_path, content_type=artifact.content_type)
        except StorageError:
            continue
        storage_id = f"sto-{uuid4().hex[:10]}"
        artifact.metadata_json = {
            **metadata_json,
            "storageObjectId": storage_id,
            "storage": {
                "backend": stored_object.backend,
                "bucket": stored_object.bucket,
                "objectKey": stored_object.object_key,
                "localPath": str(stored_object.local_path),
            },
        }
        db.add(
            StorageObject(
                id=storage_id,
                backend=stored_object.backend,
                bucket=stored_object.bucket,
                object_key=stored_object.object_key,
                local_path=str(stored_object.local_path),
                original_filename=artifact_path.name,
                content_type=artifact.content_type,
                byte_size=stored_object.byte_size,
                checksum_sha256=stored_object.checksum_sha256,
                lifecycle_state="active",
                owner=source.created_by,
                source_id=source.id,
                artifact_id=artifact_id,
                metadata_json=stored_object.metadata,
                created_at=now,
                updated_at=now,
            )
        )


def _build_multimodal_artifact_manifest(source: Source, metadata: dict, source_file: Path | None = None) -> list[dict]:
    artifacts: list[dict] = []
    ordered_blocks = metadata.get("orderedBlocks") if isinstance(metadata.get("orderedBlocks"), list) else []
    section_summaries = metadata.get("sectionSummaries") if isinstance(metadata.get("sectionSummaries"), list) else []
    source_sections = metadata.get("sourceSections") if isinstance(metadata.get("sourceSections"), list) else []
    notebook_context = metadata.get("notebookContext") if isinstance(metadata.get("notebookContext"), dict) else None
    docling_metadata = metadata.get("docling") if isinstance(metadata.get("docling"), dict) else None

    if docling_metadata:
        artifacts.append(
            {
                "id": f"{source.id}-ocr",
                "sourceId": source.id,
                "artifactType": "ocr",
                "title": "OCR And Document Parsing",
                "status": "available",
                "contentType": source.mime_type,
                "summary": f"Parser {docling_metadata.get('inputFormat') or source.source_type} with {int(docling_metadata.get('pageCount') or 0)} pages",
                "previewText": _clean_preview_text(", ".join(docling_metadata.get("ocrLanguages") or [])),
                "url": None,
                "pageNumber": None,
                "metadataJson": docling_metadata,
            }
        )

    if section_summaries or source_sections:
        artifacts.append(
            {
                "id": f"{source.id}-structure",
                "sourceId": source.id,
                "artifactType": "structure",
                "title": "Document Structure Map",
                "status": "available",
                "contentType": "application/json",
                "summary": f"{len(section_summaries)} section summaries and {len(source_sections)} section objects",
                "previewText": _clean_preview_text(", ".join(str(item.get("title") or "Untitled") for item in section_summaries[:4])),
                "url": None,
                "pageNumber": None,
                "metadataJson": {
                    "sectionSummaries": section_summaries,
                    "sourceSections": source_sections,
                },
            }
        )

    if notebook_context:
        prompts = notebook_context.get("recommendedPrompts") if isinstance(notebook_context.get("recommendedPrompts"), list) else []
        artifacts.append(
            {
                "id": f"{source.id}-notebook",
                "sourceId": source.id,
                "artifactType": "notebook",
                "title": "Notebook Context",
                "status": "available",
                "contentType": "application/json",
                "summary": f"{len(prompts)} suggested prompts prepared from source evidence",
                "previewText": _clean_preview_text("\n".join(str(prompt) for prompt in prompts[:3])),
                "url": None,
                "pageNumber": None,
                "metadataJson": notebook_context,
            }
        )

    previous_paragraph = ""
    image_index = 0
    table_index = 0
    for block in ordered_blocks:
        block_type = str(block.get("type") or "").lower()
        if block_type == "paragraph":
            previous_paragraph = str(block.get("content") or "").strip()
            continue
        if block_type == "image" and block.get("url"):
            image_index += 1
            image_path = _resolve_public_upload_path(str(block.get("url")))
            image_summary, image_preview, caption_source = _caption_image_with_context(
                source,
                image_path,
                context_before=previous_paragraph,
                alt_text=str(block.get("alt") or ""),
            )
            artifacts.append(
                {
                    "id": f"{source.id}-ordered-image-{image_index}",
                    "sourceId": source.id,
                    "artifactType": "image",
                    "title": str(block.get("alt") or f"Image Artifact {image_index}"),
                    "status": "available",
                    "contentType": infer_mime_type(image_path.name, None) if image_path else None,
                    "summary": image_summary,
                    "previewText": image_preview,
                    "url": str(block.get("url")),
                    "pageNumber": None,
                    "metadataJson": {
                        "orderedBlock": block,
                        "contextBefore": _clean_preview_text(previous_paragraph, limit=400),
                        "captionSource": caption_source,
                        "resolvedImagePath": str(image_path) if image_path else None,
                    },
                }
            )
        if block_type == "table" and block.get("content"):
            table_index += 1
            artifacts.append(
                {
                    "id": f"{source.id}-ordered-table-{table_index}",
                    "sourceId": source.id,
                    "artifactType": "table",
                    "title": f"Ordered Table {table_index}",
                    "status": "available",
                    "contentType": "text/markdown",
                    "summary": _clean_preview_text(previous_paragraph, limit=220) or "Table preserved from ordered source walkthrough",
                    "previewText": _clean_preview_text(block.get("content")),
                    "url": None,
                    "pageNumber": None,
                    "metadataJson": {"orderedBlock": block, "contextBefore": _clean_preview_text(previous_paragraph, limit=400)},
                }
            )

    if source.source_type == "image_ocr" and source_file and source_file.exists():
        image_summary, image_preview, caption_source = _caption_image_with_context(
            source,
            source_file,
            context_before=metadata.get("summary") or source.description or source.title,
            alt_text=source.title,
        )
        artifacts.append(
            {
                "id": f"{source.id}-original-image",
                "sourceId": source.id,
                "artifactType": "image",
                "title": source.title or "Uploaded image",
                "status": "available",
                "contentType": source.mime_type,
                "summary": image_summary,
                "previewText": image_preview or source_file.name,
                "url": public_upload_url(source_file),
                "pageNumber": 1,
                "metadataJson": {
                    "origin": "source_upload",
                    "filename": source_file.name,
                    "captionSource": caption_source,
                    "resolvedImagePath": str(source_file),
                },
            }
        )

    return artifacts


def get_source_artifacts(db: Session, source_id: str, actor=None) -> list[dict]:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return []
    if actor is not None and not can_access_collection_id(actor, source.collection_id):
        return []

    persisted = (
        db.query(SourceArtifactRecord)
        .filter(SourceArtifactRecord.source_id == source.id)
        .order_by(SourceArtifactRecord.artifact_type.asc(), SourceArtifactRecord.title.asc())
        .all()
    )
    if persisted:
        return [
            {
                "id": row.id,
                "sourceId": row.source_id,
                "artifactType": row.artifact_type,
                "title": row.title,
                "status": row.status,
                "contentType": row.content_type,
                "summary": row.summary,
                "previewText": row.preview_text,
                "url": row.url,
                "pageNumber": row.page_number,
                "metadataJson": row.metadata_json or {},
            }
            for row in persisted
        ]

    artifacts: list[dict] = []
    metadata = source.metadata_json or {}
    source_file = Path(source.file_path) if source.file_path else None
    seen_image_urls: set[str] = set()

    manifest = metadata.get("multimodalArtifacts") if isinstance(metadata.get("multimodalArtifacts"), list) else []
    if manifest:
        for item in manifest:
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            artifacts.append(normalized)
            if normalized.get("artifactType") == "image" and normalized.get("url"):
                seen_image_urls.add(str(normalized.get("url")))

    docling_metadata = metadata.get("docling") if isinstance(metadata.get("docling"), dict) else None
    if docling_metadata:
        page_count = int(docling_metadata.get("pageCount") or 0)
        languages = ", ".join(docling_metadata.get("ocrLanguages") or [])
        summary_parts = [f"Parser: {docling_metadata.get('inputFormat') or source.source_type}"]
        if page_count:
            summary_parts.append(f"{page_count} pages")
        if languages:
            summary_parts.append(f"OCR languages: {languages}")
        artifacts.append(
            {
                "id": f"{source.id}-ocr",
                "sourceId": source.id,
                "artifactType": "ocr",
                "title": "OCR And Document Parsing",
                "status": "available",
                "contentType": source.mime_type,
                "summary": " | ".join(summary_parts),
                "previewText": None,
                "url": None,
                "pageNumber": None,
                "metadataJson": docling_metadata,
            }
        )

    section_summaries = metadata.get("sectionSummaries") if isinstance(metadata.get("sectionSummaries"), list) else []
    source_sections = metadata.get("sourceSections") if isinstance(metadata.get("sourceSections"), list) else []
    if section_summaries or source_sections:
        top_titles = ", ".join(str(item.get("title") or "Untitled") for item in section_summaries[:4])
        artifacts.append(
            {
                "id": f"{source.id}-structure",
                "sourceId": source.id,
                "artifactType": "structure",
                "title": "Document Structure Map",
                "status": "available",
                "contentType": "application/json",
                "summary": f"{len(section_summaries)} section summaries, {len(source_sections)} source sections",
                "previewText": top_titles or None,
                "url": None,
                "pageNumber": None,
                "metadataJson": {
                    "sectionSummaries": section_summaries,
                    "sourceSections": source_sections,
                },
            }
        )

    notebook_context = metadata.get("notebookContext") if isinstance(metadata.get("notebookContext"), dict) else None
    if notebook_context:
        prompts = notebook_context.get("recommendedPrompts") if isinstance(notebook_context.get("recommendedPrompts"), list) else []
        artifacts.append(
            {
                "id": f"{source.id}-notebook",
                "sourceId": source.id,
                "artifactType": "notebook",
                "title": "Notebook Context",
                "status": "available",
                "contentType": "application/json",
                "summary": f"{len(prompts)} suggested prompts for guided exploration",
                "previewText": "\n".join(str(prompt) for prompt in prompts[:3]) if prompts else None,
                "url": None,
                "pageNumber": None,
                "metadataJson": notebook_context,
            }
        )

    ordered_blocks = metadata.get("orderedBlocks") if isinstance(metadata.get("orderedBlocks"), list) else []
    if ordered_blocks:
        image_index = 0
        table_index = 0
        for block in ordered_blocks:
            block_type = str(block.get("type") or "").lower()
            if block_type == "image" and block.get("url"):
                image_index += 1
                image_url = str(block.get("url"))
                seen_image_urls.add(image_url)
                artifacts.append(
                    {
                        "id": f"{source.id}-ordered-image-{image_index}",
                        "sourceId": source.id,
                        "artifactType": "image",
                        "title": str(block.get("alt") or f"Image Artifact {image_index}"),
                        "status": "available",
                        "contentType": None,
                        "summary": "Image referenced from ordered source walkthrough",
                        "previewText": str(block.get("alt") or ""),
                        "url": image_url,
                        "pageNumber": None,
                        "metadataJson": {"orderedBlock": block},
                    }
                )
            if block_type == "table" and block.get("content"):
                table_index += 1
                artifacts.append(
                    {
                        "id": f"{source.id}-ordered-table-{table_index}",
                        "sourceId": source.id,
                        "artifactType": "table",
                        "title": f"Ordered Table {table_index}",
                        "status": "available",
                        "contentType": "text/markdown",
                        "summary": "Table preserved from ordered source walkthrough",
                        "previewText": str(block.get("content"))[:600],
                        "url": None,
                        "pageNumber": None,
                        "metadataJson": {"orderedBlock": block},
                    }
                )

    if source_file:
        if source.source_type == "image_ocr" and source_file.exists():
            original_image_url = public_upload_url(source_file)
            if original_image_url not in seen_image_urls:
                seen_image_urls.add(original_image_url)
                artifacts.append(
                    {
                        "id": f"{source.id}-original-image",
                        "sourceId": source.id,
                        "artifactType": "image",
                        "title": source.title or "Uploaded image",
                        "status": "available",
                        "contentType": source.mime_type,
                        "summary": "Original uploaded image preserved for OCR and multimodal review",
                        "previewText": source_file.name,
                        "url": original_image_url,
                        "pageNumber": 1,
                        "metadataJson": {"origin": "source_upload", "filename": source_file.name},
                    }
                )
        assets_dir = ensure_upload_dir() / f"{source_file.stem}-assets"
        if assets_dir.exists():
            image_files = sorted(
                [
                    path
                    for path in assets_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
                ]
            )
            for index, path in enumerate(image_files, start=1):
                asset_url = public_upload_url(path)
                if asset_url in seen_image_urls:
                    continue
                artifacts.append(
                    {
                        "id": f"{source.id}-image-{index}",
                        "sourceId": source.id,
                        "artifactType": "image",
                        "title": f"Image Artifact {index}",
                        "status": "available",
                        "contentType": infer_mime_type(path.name, None),
                        "summary": f"Extracted image asset from `{source.title}`",
                        "previewText": path.name,
                        "url": asset_url,
                        "pageNumber": None,
                        "metadataJson": {"filename": path.name},
                    }
                )

    table_like_chunks = (
        db.query(SourceChunk)
        .filter(SourceChunk.source_id == source.id)
        .order_by(SourceChunk.chunk_index.asc())
        .all()
    )
    table_count = 0
    for chunk in table_like_chunks:
        chunk_metadata = chunk.metadata_json or {}
        block_types = [str(item).lower() for item in (chunk_metadata.get("blockTypes") or []) if str(item).strip()]
        looks_like_table = "table" in block_types or str(chunk.content or "").count("|") >= 4
        if not looks_like_table:
            continue
        table_count += 1
        artifacts.append(
            {
                "id": f"{source.id}-table-{table_count}",
                "sourceId": source.id,
                "artifactType": "table",
                "title": chunk.section_title or f"Table Artifact {table_count}",
                "status": "available",
                "contentType": "text/markdown",
                "summary": f"Structured table candidate from chunk {chunk.chunk_index + 1}",
                "previewText": chunk.content[:600],
                "url": None,
                "pageNumber": chunk.page_number,
                "metadataJson": {
                    "chunkId": chunk.id,
                    "chunkIndex": chunk.chunk_index,
                    "blockTypes": block_types,
                },
            }
        )

    deduped: list[dict] = []
    seen_ids: set[str] = set()
    for item in artifacts:
        item_id = str(item.get("id") or "")
        if item_id and item_id in seen_ids:
            continue
        if item_id:
            seen_ids.add(item_id)
        deduped.append(item)

    deduped.sort(key=lambda item: (item["artifactType"], item["title"]))
    return deduped


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


def update_source_metadata(
    db: Session,
    source_id: str,
    *,
    actor: str = "Current User",
    description: str | None = None,
    tags: list[str] | None = None,
    trust_level: str | None = None,
    document_type: str | None = None,
    source_status: str | None = None,
    authority_level: str | None = None,
    effective_date: str | None = None,
    version: str | None = None,
    owner: str | None = None,
) -> dict | None:
    from app.services.audit import create_audit_log

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None

    metadata = dict(source.metadata_json or {})
    changes: dict[str, object] = {}

    if description is not None:
        source.description = _string_or_none(description)
        changes["description"] = source.description
    if tags is not None:
        cleaned_tags: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            cleaned = _string_or_none(tag)
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned_tags.append(cleaned)
        source.tags = cleaned_tags
        changes["tags"] = cleaned_tags
    if trust_level is not None:
        normalized_trust = (_string_or_none(trust_level) or "").lower()
        if normalized_trust not in SOURCE_TRUST_LEVELS:
            raise ValueError("trustLevel must be one of: high, medium, low")
        source.trust_level = normalized_trust
        changes["trustLevel"] = normalized_trust

    metadata_updates = {
        "documentType": _string_or_none(document_type) if document_type is not None else None,
        "sourceStatus": _string_or_none(source_status) if source_status is not None else None,
        "authorityLevel": _string_or_none(authority_level) if authority_level is not None else None,
        "effectiveDate": _string_or_none(effective_date) if effective_date is not None else None,
        "version": _string_or_none(version) if version is not None else None,
        "owner": _string_or_none(owner) if owner is not None else None,
    }
    if metadata_updates["sourceStatus"] is not None and metadata_updates["sourceStatus"].lower() not in SOURCE_STATUS_VALUES:
        raise ValueError("sourceStatus must be one of: draft, approved, archived, superseded")
    if metadata_updates["authorityLevel"] is not None and metadata_updates["authorityLevel"].lower() not in AUTHORITY_LEVEL_VALUES:
        raise ValueError("authorityLevel must be one of: official, reference, informal")

    for key, value in metadata_updates.items():
        if value is None:
            continue
        normalized_value = value.lower() if key in {"sourceStatus", "authorityLevel"} else value
        metadata[key] = normalized_value
        changes[key] = normalized_value

    source.metadata_json = metadata
    source.updated_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        action="update_source_metadata",
        object_type="source",
        object_id=source.id,
        actor=actor,
        summary=f"Updated metadata for source `{source.title}`",
        metadata={"changes": changes},
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
    source_id = f"src-{uuid4().hex[:8]}"
    stored_object = save_source_object(filename, file_bytes, content_type=resolved_mime_type)
    stored_path = stored_object.local_path
    checksum = stored_object.checksum_sha256
    duplicate_source = db.query(Source).filter(Source.checksum == checksum).order_by(Source.uploaded_at.asc()).first()
    enriched_metadata = {
        **(metadata or {}),
        "storage": {
            "backend": stored_object.backend,
            "bucket": stored_object.bucket,
            "objectKey": stored_object.object_key,
            "localPath": str(stored_path),
        },
        "dedupe": {"checksum": checksum, "duplicateOfSourceId": duplicate_source.id if duplicate_source else None},
        "sourceStatus": _string_or_none((metadata or {}).get("sourceStatus")) or "draft",
        "authorityLevel": _string_or_none((metadata or {}).get("authorityLevel")) or "reference",
        "owner": _string_or_none((metadata or {}).get("owner")) or actor,
    }

    source = Source(
        id=source_id,
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
    db.add(
        StorageObject(
            id=f"sto-{uuid4().hex[:10]}",
            backend=stored_object.backend,
            bucket=stored_object.bucket,
            object_key=stored_object.object_key,
            local_path=str(stored_path),
            original_filename=filename,
            content_type=resolved_mime_type,
            byte_size=stored_object.byte_size,
            checksum_sha256=stored_object.checksum_sha256,
            lifecycle_state="active",
            owner=actor,
            source_id=source_id,
            metadata_json=stored_object.metadata,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
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
    storage_object = (
        db.query(StorageObject)
        .filter(StorageObject.source_id == source.id, StorageObject.lifecycle_state == "active")
        .order_by(StorageObject.created_at.desc())
        .first()
    )
    refresh_object_bytes(
        storage_object.object_key if storage_object else source.file_path,
        storage_object.local_path if storage_object else source.file_path,
        file_bytes,
        content_type="text/plain",
    )
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
    if storage_object:
        storage_object.byte_size = len(file_bytes)
        storage_object.checksum_sha256 = source.checksum
        storage_object.content_type = "text/plain"
        storage_object.updated_at = source.updated_at
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
        if key in {"inputConnector", "sourceKind", "originalTitle", "fetchedUrl", "contentType", "sourceContentType", "validation", "rawBytes", "readableCharCount", "charCountOriginal", "sourceStatus", "authorityLevel", "effectiveDate", "version", "owner"}
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
        section_summaries = list(parsed.metadata.get("sectionSummaries", []))
        source_sections = list(parsed.metadata.get("sourceSections", []))
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
            "keywords": list(parsed.metadata.get("keywords", tags)),
            "language": parsed.metadata.get("language"),
            "pipelineStages": serialize_stage_results(artifacts.stage_results),
            "pageTypeCandidates": page_type_candidates,
            "timelineEvents": timeline_events,
            "glossaryTerms": glossary_terms,
            "sectionSummaries": section_summaries,
            "sourceSections": source_sections,
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
            heading_path = [str(part) for part in (chunk_metadata.get("headingPath") or []) if str(part).strip()]
            section_key_hint = " > ".join(heading_path) or str(chunk.get("section_title") or "Document")
            parent_section = next(
                (
                    section
                    for section in section_summaries
                    if (
                        (heading_path and list(section.get("headingPath") or []) == heading_path)
                        or str(section.get("title") or "") == str(chunk.get("section_title") or "")
                        or str(section.get("sectionKey") or "").endswith(slugify(section_key_hint))
                    )
                ),
                None,
            )
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
                    "keywords": tags[:6],
                    "language": parsed.metadata.get("language"),
                    "parentSectionKey": parent_section.get("sectionKey") if parent_section else None,
                    "parentSectionSummary": parent_section.get("summary") if parent_section else None,
                    "parentSectionTitle": parent_section.get("title") if parent_section else None,
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
            claim_metadata = dict(claim_payload.get("metadata_json") or {})
            claim_metadata.setdefault("documentType", parsed.metadata.get("documentType"))
            claim_metadata.setdefault("language", parsed.metadata.get("language"))
            claim_metadata.setdefault("keywords", tags[:6])
            claim_metadata.setdefault("sourceStatus", source.metadata_json.get("sourceStatus"))
            claim_metadata.setdefault("authorityLevel", source.metadata_json.get("authorityLevel"))
            claim_metadata.setdefault("sourceOwner", source.metadata_json.get("owner"))
            claim_metadata.setdefault("sectionRole", (chunk_record.metadata_json or {}).get("sectionRole"))
            claim_metadata.setdefault("parentSectionKey", (chunk_record.metadata_json or {}).get("parentSectionKey"))
            claim_metadata.setdefault("parentSectionTitle", (chunk_record.metadata_json or {}).get("parentSectionTitle"))
            claim_metadata.setdefault("parentSectionSummary", (chunk_record.metadata_json or {}).get("parentSectionSummary"))
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
                metadata_json=claim_metadata,
            )
            db.add(claim)
            claim_records.append((claim, chunk_record))

        knowledge_unit_records: list[KnowledgeUnit] = []
        for claim, chunk_record in claim_records:
            metadata_json = dict(claim.metadata_json or {})
            metadata_json.setdefault("sourceChunkIndex", chunk_record.chunk_index)
            metadata_json.setdefault("sourceChunkSectionTitle", chunk_record.section_title)
            metadata_json.setdefault("origin", "claim_extraction")
            metadata_json.setdefault("documentType", parsed.metadata.get("documentType"))
            metadata_json.setdefault("language", parsed.metadata.get("language"))
            metadata_json.setdefault("keywords", tags[:6])
            normalized_unit_type = _normalize_knowledge_unit_type(claim, metadata_json)
            metadata_json.setdefault("originalClaimType", claim.claim_type)
            unit = KnowledgeUnit(
                id=f"ku-{uuid4().hex[:8]}",
                source_id=source.id,
                source_chunk_id=chunk_record.id,
                claim_id=claim.id,
                unit_type=normalized_unit_type,
                title=(claim.topic or normalized_unit_type.replace("_", " ").title())[:255],
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

        notebook_context = _build_notebook_context(
            source,
            summary,
            key_facts,
            section_summaries,
            source_sections,
            claim_records,
            knowledge_unit_records,
        )
        source.metadata_json = {
            **(source.metadata_json or {}),
            "notebookContext": notebook_context,
        }
        multimodal_artifacts = _build_multimodal_artifact_manifest(
            source,
            source.metadata_json or {},
            stored_path,
        )
        source.metadata_json = {
            **(source.metadata_json or {}),
            "multimodalArtifacts": multimodal_artifacts,
        }
        _persist_source_artifacts(db, source, multimodal_artifacts)

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
