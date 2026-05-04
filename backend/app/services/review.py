from __future__ import annotations

import difflib
from datetime import datetime, timedelta, timezone
import re
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.ingest import build_tags, slugify
from app.models import Claim, Page, PageLink, PageSourceLink, PageVersion, ReviewComment, ReviewItem, Source, SourceChunk
from app.services.audit import create_audit_log
from app.services.pages import create_page_with_version, get_page_by_slug


NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")
SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _aware(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _page_source_ids(db: Session, page_id: str) -> list[str]:
    return [source_id for (source_id,) in db.query(PageSourceLink.source_id).filter(PageSourceLink.page_id == page_id).all()]


def _page_backlinks(db: Session, page: Page) -> list[dict]:
    backlinks: list[dict] = []
    referring_ids = [page_id for (page_id,) in db.query(PageLink.from_page_id).filter(PageLink.to_page_id == page.id).all()]
    if referring_ids:
        for ref_page in db.query(Page).filter(Page.id.in_(referring_ids)).all():
            backlinks.append({"id": ref_page.id, "slug": ref_page.slug, "title": ref_page.title, "relationType": "linked"})
    for ref_page in db.query(Page).filter(Page.related_page_ids.isnot(None)).all():
        if page.id in (ref_page.related_page_ids or []):
            entry = {"id": ref_page.id, "slug": ref_page.slug, "title": ref_page.title, "relationType": "related_to"}
            if entry not in backlinks:
                backlinks.append(entry)
    return sorted(backlinks, key=lambda item: item["title"].lower())


def _build_diff_lines(old_content: str, new_content: str) -> tuple[list[dict], dict]:
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)

    diff_lines: list[dict] = []
    stats = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, text in enumerate(old_lines[i1:i2]):
                diff_lines.append(
                    {
                        "kind": "unchanged",
                        "oldLineNumber": i1 + offset + 1,
                        "newLineNumber": j1 + offset + 1,
                        "oldText": text,
                        "newText": text,
                    }
                )
                stats["unchanged"] += 1
            continue

        if tag == "replace":
            old_slice = old_lines[i1:i2]
            new_slice = new_lines[j1:j2]
            max_len = max(len(old_slice), len(new_slice))
            for offset in range(max_len):
                old_text = old_slice[offset] if offset < len(old_slice) else ""
                new_text = new_slice[offset] if offset < len(new_slice) else ""
                kind = "modified" if old_text and new_text else ("removed" if old_text else "added")
                diff_lines.append(
                    {
                        "kind": kind,
                        "oldLineNumber": i1 + offset + 1 if old_text else None,
                        "newLineNumber": j1 + offset + 1 if new_text else None,
                        "oldText": old_text,
                        "newText": new_text,
                    }
                )
                stats[kind] += 1
            continue

        if tag == "delete":
            for offset, text in enumerate(old_lines[i1:i2]):
                diff_lines.append(
                    {
                        "kind": "removed",
                        "oldLineNumber": i1 + offset + 1,
                        "newLineNumber": None,
                        "oldText": text,
                        "newText": "",
                    }
                )
                stats["removed"] += 1
            continue

        if tag == "insert":
            for offset, text in enumerate(new_lines[j1:j2]):
                diff_lines.append(
                    {
                        "kind": "added",
                        "oldLineNumber": None,
                        "newLineNumber": j1 + offset + 1,
                        "oldText": "",
                        "newText": text,
                    }
                )
                stats["added"] += 1

    return diff_lines, stats


def _page_context(db: Session, page: Page, source_ids: list[str], backlinks: list[dict]) -> dict:
    return {
        "id": page.id,
        "slug": page.slug,
        "title": page.title,
        "status": page.status,
        "pageType": page.page_type,
        "sourceIds": source_ids,
        "sourceCount": len(source_ids),
        "relatedPageIds": page.related_page_ids or [],
        "relatedEntityIds": page.related_entity_ids or [],
        "backlinks": backlinks,
    }


def _change_set(
    old_content: str,
    new_content: str,
    change_summary: str,
    previous_version: int | None,
    review_level: str,
    issue_count: int,
) -> dict:
    diff_lines, stats = _build_diff_lines(old_content or "", new_content or "")
    return {
        "summary": change_summary,
        "hasContentChanges": old_content != new_content,
        "reviewLevel": review_level,
        "previousVersion": previous_version,
        "proposedVersion": (previous_version + 1) if previous_version is not None and old_content != new_content else previous_version,
        "issueCount": issue_count,
        "stats": {
            "addedLines": stats["added"],
            "removedLines": stats["removed"],
            "modifiedLines": stats["modified"],
            "unchangedLines": stats["unchanged"],
        },
        "diffLines": diff_lines,
    }


def _review_actions(item_id: str, suggestions: list[dict], is_virtual: bool) -> dict:
    return {
        "canApprove": True,
        "canReject": not is_virtual or True,
        "canMerge": any(suggestion.get("type") == "page_match" and suggestion.get("targetId") for suggestion in suggestions),
        "canRequestRebuild": True,
        "primaryAction": "approve_page" if is_virtual else "approve_update",
        "secondaryActions": ["merge", "reject", "rebuild"] if suggestions else ["reject", "rebuild"],
        "itemId": item_id,
    }


def _text_overlap_score(left: str, right: str) -> float:
    left_terms = {token for token in re.findall(r"[a-z0-9_/-]+", left.lower()) if len(token) >= 3}
    right_terms = {token for token in re.findall(r"[a-z0-9_/-]+", right.lower()) if len(token) >= 3}
    if not left_terms or not right_terms:
        return 0.0
    overlap = len(left_terms & right_terms)
    return overlap / max(min(len(left_terms), len(right_terms)), 1)


def _match_suggestions(db: Session, page: Page, source_ids: list[str]) -> list[dict]:
    suggestions: list[dict] = []
    source_bundle = " ".join(
        f"{source.title} {source.description or ''} {' '.join(source.tags or [])}"
        for source in db.query(Source).filter(Source.id.in_(source_ids)).all()
    ) if source_ids else page.content_md

    for candidate in db.query(Page).filter(Page.id != page.id).all():
        score = _text_overlap_score(source_bundle, f"{candidate.title} {candidate.summary} {' '.join(candidate.tags or [])}")
        if score >= 0.2:
            suggestions.append(
                {
                    "type": "page_match",
                    "title": candidate.title,
                    "targetId": candidate.id,
                    "targetSlug": candidate.slug,
                    "confidenceScore": round(min(0.55 + score, 0.95), 2),
                    "reason": "Overlapping source and page vocabulary suggests a related page link.",
                }
            )

    entity_names = [name for (name,) in db.query(Source.title).filter(Source.id.in_(source_ids)).all()]
    for entity in db.query(SourceChunk.section_title).join(Source, SourceChunk.source_id == Source.id).filter(Source.id.in_(source_ids)).distinct().all():
        section_title = entity[0]
        if not section_title or section_title == "Document":
            continue
        suggestions.append(
            {
                "type": "section_link",
                "title": section_title,
                "targetId": None,
                "targetSlug": None,
                "confidenceScore": 0.6,
                "reason": "Source sections can be converted into backlinks, child pages, or section anchors.",
            }
        )
    return sorted(suggestions, key=lambda item: item["confidenceScore"], reverse=True)[:6]


def _stale_heuristic_issues(db: Session, page: Page, source_ids: list[str]) -> list[dict]:
    issues: list[dict] = []
    now = datetime.now(timezone.utc)
    reference_time = _aware(page.last_reviewed_at or page.published_at or page.last_composed_at)
    if reference_time and reference_time < now - timedelta(days=45):
        issues.append(
            {
                "type": "stale_content",
                "severity": "medium",
                "message": "Page has not been reviewed in more than 45 days.",
                "evidence": f"Last review reference is {_iso(reference_time)}.",
                "sourceChunkId": None,
                "claimId": None,
            }
        )

    if source_ids:
        newer_sources = [
            source
            for source in db.query(Source).filter(Source.id.in_(source_ids)).all()
            if reference_time and _aware(source.updated_at) and _aware(source.updated_at) > reference_time
        ]
        if newer_sources:
            issues.append(
                {
                    "type": "stale_content",
                    "severity": "high",
                    "message": "At least one linked source was updated after this page was last reviewed.",
                    "evidence": ", ".join(f"{source.title} ({_iso(source.updated_at)})" for source in newer_sources[:3]),
                    "sourceChunkId": None,
                    "claimId": None,
                }
            )
    return issues


def _conflict_heuristic_issues(db: Session, page: Page, source_ids: list[str]) -> list[dict]:
    if len(source_ids) < 2:
        return []

    rows = (
        db.query(Claim, Source)
        .join(SourceChunk, Claim.source_chunk_id == SourceChunk.id)
        .join(Source, SourceChunk.source_id == Source.id)
        .filter(Source.id.in_(source_ids))
        .all()
    )

    values_by_topic: dict[str, dict[str, set[str]]] = {}
    for claim, source in rows:
        numbers = set(NUMBER_RE.findall(claim.text or ""))
        if not numbers:
            continue
        topic = (claim.topic or "general").lower()
        values_by_topic.setdefault(topic, {}).setdefault(source.title, set()).update(numbers)

    issues: list[dict] = []
    for topic, source_values in values_by_topic.items():
        normalized = {tuple(sorted(values)) for values in source_values.values() if values}
        if len(normalized) <= 1:
            continue
        evidence = "; ".join(f"{source}: {', '.join(sorted(values))}" for source, values in list(source_values.items())[:3])
        issues.append(
            {
                "type": "conflict_detected",
                "severity": "high",
                "message": f"Linked sources contain conflicting numeric values for topic '{topic}'.",
                "evidence": evidence,
                "sourceChunkId": None,
                "claimId": None,
            }
        )
    return issues[:3]


def _low_confidence_claim_issues(db: Session, page: Page, source_ids: list[str]) -> list[dict]:
    if not source_ids:
        return []
    rows = (
        db.query(Claim, SourceChunk)
        .join(SourceChunk, Claim.source_chunk_id == SourceChunk.id)
        .filter(SourceChunk.source_id.in_(source_ids))
        .order_by(Claim.confidence_score.asc(), Claim.extracted_at.desc())
        .limit(6)
        .all()
    )
    issues: list[dict] = []
    for claim, chunk in rows:
        if claim.confidence_score >= 0.62 and not (claim.metadata_json or {}).get("isLowConfidence"):
            continue
        issues.append(
            {
                "type": "low_confidence",
                "severity": "medium" if claim.confidence_score >= 0.45 else "high",
                "message": f"Claim `{claim.text[:120]}` was extracted with low confidence.",
                "evidence": f"Chunk `{chunk.id}` / confidence={claim.confidence_score} / method={claim.extraction_method}",
                "sourceChunkId": chunk.id,
                "claimId": claim.id,
            }
        )
    return issues


def _serialize_issue(issue: dict | object) -> dict:
    if isinstance(issue, dict):
        return issue
    return {
        "type": issue.issue_type,
        "severity": issue.severity,
        "message": issue.message,
        "evidence": issue.evidence,
        "sourceChunkId": issue.source_chunk_id,
        "claimId": issue.claim_id,
    }


def _build_virtual_review_items(db: Session) -> list[dict]:
    virtuals: list[dict] = []
    pages = db.query(Page).filter(Page.status.in_(["published", "stale", "in_review"])).all()
    for page in pages:
        source_ids = _page_source_ids(db, page.id)
        heuristic_issues = _stale_heuristic_issues(db, page, source_ids) + _conflict_heuristic_issues(db, page, source_ids) + _low_confidence_claim_issues(db, page, source_ids)
        by_type: dict[str, list[dict]] = {}
        for issue in heuristic_issues:
            by_type.setdefault(issue["type"], []).append(issue)
        for issue_type, issues in by_type.items():
            backlinks = _page_backlinks(db, page)
            suggestions = _match_suggestions(db, page, source_ids)
            severity = max((issue["severity"] for issue in issues), key=lambda item: SEVERITY_ORDER.index(item))
            virtuals.append(
                {
                    "id": f"virtual-{issue_type}-{page.id}",
                    "pageId": page.id,
                    "pageTitle": page.title,
                    "pageSlug": page.slug,
                    "pageStatus": page.status,
                    "issueType": issue_type,
                    "severity": severity,
                    "issues": issues,
                    "oldContentMd": page.content_md,
                    "newContentMd": page.content_md,
                    "changeSummary": f"Auto-detected {issue_type.replace('_', ' ')} heuristic",
                    "confidenceScore": 0.72 if issue_type == "stale_content" else 0.81,
                    "createdAt": _iso(page.last_composed_at),
                    "updatedAt": _iso(datetime.now(timezone.utc)),
                    "assignedTo": None,
                    "previousVersion": page.current_version,
                    "sourceIds": source_ids,
                    "evidenceSnippets": [],
                    "reviewLevel": "page",
                    "itemKind": "heuristic",
                    "suggestions": suggestions,
                    "backlinks": backlinks,
                    "pageContext": _page_context(db, page, source_ids, backlinks),
                    "changeSet": _change_set(page.content_md, page.content_md, f"Auto-detected {issue_type.replace('_', ' ')} heuristic", page.current_version, "page", len(issues)),
                    "reviewActions": _review_actions(f"virtual-{issue_type}-{page.id}", suggestions, True),
                    "isVirtual": True,
                }
            )
    return virtuals


def serialize_review_item(review_item: ReviewItem, db: Session | None = None) -> dict:
    issues = [_serialize_issue(issue) for issue in review_item.issues]
    page = db.query(Page).filter(Page.id == review_item.page_id).first() if db is not None else None
    source_ids = review_item.source_ids or []
    heuristic_issues = []
    suggestions = []
    backlinks = []
    comments = []
    if db is not None and page is not None:
        heuristic_issues = _stale_heuristic_issues(db, page, source_ids) + _conflict_heuristic_issues(db, page, source_ids) + _low_confidence_claim_issues(db, page, source_ids)
        suggestions = _match_suggestions(db, page, source_ids)
        backlinks = _page_backlinks(db, page)
        comments = list_review_comments(db, review_item.id)
    page_context = _page_context(db, page, source_ids, backlinks) if db is not None and page is not None else None
    combined_issues = issues + heuristic_issues
    return {
        "id": review_item.id,
        "pageId": review_item.page_id,
        "pageTitle": review_item.page_title,
        "pageSlug": review_item.page_slug,
        "pageStatus": review_item.page_status,
        "issueType": review_item.issue_type,
        "severity": review_item.severity,
        "issues": combined_issues,
        "oldContentMd": review_item.old_content_md,
        "newContentMd": review_item.new_content_md,
        "changeSummary": review_item.change_summary,
        "confidenceScore": review_item.confidence_score,
        "createdAt": _iso(review_item.created_at),
        "updatedAt": _iso(review_item.updated_at),
        "assignedTo": review_item.assigned_to,
        "previousVersion": review_item.previous_version,
        "sourceIds": source_ids,
        "evidenceSnippets": review_item.evidence_snippets or [],
        "reviewLevel": "update",
        "itemKind": "generated_update",
        "suggestions": suggestions,
        "backlinks": backlinks,
        "comments": comments,
        "pageContext": page_context,
        "changeSet": _change_set(
            review_item.old_content_md,
            review_item.new_content_md,
            review_item.change_summary,
            review_item.previous_version,
            "update",
            len(combined_issues),
        ),
        "reviewActions": _review_actions(review_item.id, suggestions, False),
        "isVirtual": False,
    }


def list_review_comments(db: Session, item_id: str) -> list[dict]:
    rows = db.query(ReviewComment).filter(ReviewComment.review_item_id == item_id).order_by(ReviewComment.created_at.asc()).all()
    return [{"id": row.id, "reviewItemId": row.review_item_id, "actor": row.actor, "comment": row.comment, "createdAt": _iso(row.created_at)} for row in rows]


def add_review_comment(db: Session, item_id: str, comment: str, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    if item_id.startswith("virtual-"):
        if not get_review_item(db, item_id):
            return None
    elif not db.query(ReviewItem.id).filter(ReviewItem.id == item_id).first():
        return None
    now = datetime.now(timezone.utc)
    row = ReviewComment(
        id=f"rc-{uuid4().hex[:12]}",
        review_item_id=item_id,
        actor=actor,
        comment=comment.strip(),
        created_at=now,
    )
    db.add(row)
    create_audit_log(
        db,
        action="review_comment",
        object_type="review_item",
        object_id=item_id,
        actor=actor,
        summary=f"Commented on review item `{item_id}`",
        metadata=actor_metadata or {},
    )
    db.commit()
    return {"id": row.id, "reviewItemId": row.review_item_id, "actor": row.actor, "comment": row.comment, "createdAt": _iso(row.created_at)}


def list_review_items(db: Session, page: int = 1, page_size: int = 20, severity: str | None = None, issue_type: str | None = None) -> dict:
    persisted = [serialize_review_item(item, db) for item in db.query(ReviewItem).order_by(ReviewItem.created_at.desc()).all()]
    virtuals = _build_virtual_review_items(db)
    items = persisted + virtuals
    if severity:
        items = [item for item in items if item["severity"] == severity]
    if issue_type:
        items = [item for item in items if item["issueType"] == issue_type]
    items.sort(key=lambda item: item["createdAt"] or "", reverse=True)
    start = (page - 1) * page_size
    data = items[start : start + page_size]
    return {"data": data, "total": len(items), "page": page, "pageSize": page_size, "hasMore": start + page_size < len(items)}


def get_review_item(db: Session, item_id: str) -> dict | None:
    if item_id.startswith("virtual-"):
        return next((item for item in _build_virtual_review_items(db) if item["id"] == item_id), None)
    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    return serialize_review_item(item, db) if item else None


def approve_review_item(db: Session, item_id: str, comment: str | None = None, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    if item_id.startswith("virtual-"):
        virtual = get_review_item(db, item_id)
        if not virtual:
            return None
        page = db.query(Page).filter(Page.id == virtual["pageId"]).first()
        if not page:
            return None
        now = datetime.now(timezone.utc)
        page.status = "published"
        page.published_at = page.published_at or now
        page.last_reviewed_at = now
        create_audit_log(
            db,
            action="approve_review",
            object_type="page",
            object_id=page.id,
            actor=actor,
            summary=f"Approved virtual review `{virtual['issueType']}`",
            metadata={"reviewItemId": item_id, "comment": comment, **(actor_metadata or {})},
        )
        db.commit()
        return {"success": True, "page": get_page_by_slug(db, page.slug)}

    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if not item:
        return None
    page = db.query(Page).filter(Page.id == item.page_id).first()
    if not page:
        return None
    now = datetime.now(timezone.utc)
    page.status = "published"
    page.published_at = now
    page.last_reviewed_at = now
    item.page_status = "published"
    item.updated_at = now
    if comment:
        item.change_summary = f"{item.change_summary} | Approved: {comment}".strip(" |")
    for version in db.query(PageVersion).filter(PageVersion.page_id == page.id).all():
        if version.version_no == page.current_version:
            version.review_status = "approved"
    create_audit_log(
        db,
        action="approve_review",
        object_type="page",
        object_id=page.id,
        actor=actor,
        summary=f"Approved review update `{item.change_summary}`",
        metadata={"reviewItemId": item_id, "comment": comment, **(actor_metadata or {})},
    )
    db.delete(item)
    db.commit()
    return {"success": True, "page": get_page_by_slug(db, page.slug)}


def reject_review_item(db: Session, item_id: str, reason: str, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    if item_id.startswith("virtual-"):
        virtual = get_review_item(db, item_id)
        if not virtual:
            return None
        page = db.query(Page).filter(Page.id == virtual["pageId"]).first()
        if page:
            page.status = "draft"
            page.last_reviewed_at = datetime.now(timezone.utc)
            create_audit_log(
                db,
                action="reject_review",
                object_type="page",
                object_id=page.id,
                actor=actor,
                summary=f"Rejected virtual review `{virtual['issueType']}`",
                metadata={"reviewItemId": item_id, "reason": reason, **(actor_metadata or {})},
            )
            db.commit()
        return {"success": True}

    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if not item:
        return None
    page = db.query(Page).filter(Page.id == item.page_id).first()
    if page:
        page.status = "draft"
        create_audit_log(
            db,
            action="reject_review",
            object_type="page",
            object_id=page.id,
            actor=actor,
            summary=f"Rejected review update `{item.change_summary}`",
            metadata={"reviewItemId": item_id, "reason": reason, **(actor_metadata or {})},
        )
    item.updated_at = datetime.now(timezone.utc)
    item.change_summary = f"{item.change_summary} | Rejected: {reason}".strip(" |")
    db.commit()
    return {"success": True}


def merge_review_item(db: Session, item_id: str, target_page_id: str | None = None, comment: str | None = None, actor: str = "Current User", actor_metadata: dict | None = None) -> dict | None:
    item = get_review_item(db, item_id)
    if not item:
        return None

    source_page = db.query(Page).filter(Page.id == item["pageId"]).first()
    if not source_page:
        return None

    suggestions = item.get("suggestions", [])
    page_match_suggestions = [suggestion for suggestion in suggestions if suggestion.get("type") == "page_match" and suggestion.get("targetId")]
    target_id = target_page_id or (page_match_suggestions[0]["targetId"] if page_match_suggestions else None)
    if not target_id:
        return None

    target_page = db.query(Page).filter(Page.id == target_id, Page.id != source_page.id).first()
    if not target_page:
        return None

    source_ids = _page_source_ids(db, source_page.id)
    target_source_ids = set(_page_source_ids(db, target_page.id))
    for source_id in source_ids:
        if source_id not in target_source_ids:
            db.add(PageSourceLink(id=f"psl-{uuid4().hex[:12]}", page_id=target_page.id, source_id=source_id))
            target_source_ids.add(source_id)

    merged_entities = sorted(set(target_page.related_entity_ids or []) | set(source_page.related_entity_ids or []))
    target_page.related_entity_ids = merged_entities
    merged_related_pages = sorted(set(target_page.related_page_ids or []) | {source_page.id})
    target_page.related_page_ids = merged_related_pages

    merge_header = f"## Merged Notes From {source_page.title}"
    if merge_header not in (target_page.content_md or ""):
        merged_block = "\n\n".join(
            [
                merge_header,
                source_page.summary or "",
                "\n".join(f"- {fact}" for fact in (source_page.key_facts or [])[:5]),
            ]
        ).strip()
        target_page.content_md = (target_page.content_md.rstrip() + "\n\n" + merged_block).strip()

    now = datetime.now(timezone.utc)
    target_page.current_version += 1
    target_page.last_composed_at = now
    target_page.last_reviewed_at = now
    if comment:
        note = comment.strip()
        if note:
            target_page.summary = ((target_page.summary or "").strip() + f" | Merge note: {note}").strip(" |")[:800]

    db.add(
        PageVersion(
            id=f"pv-merge-{uuid4().hex[:12]}",
            page_id=target_page.id,
            version_no=target_page.current_version,
            content_md=target_page.content_md,
            change_summary=(comment or f"Merged content from {source_page.title}")[:255],
            created_at=now,
            created_by_agent_or_user="Review Merge",
            review_status="approved",
        )
    )

    db.add(
        PageLink(
            id=f"plink-merge-{uuid4().hex[:12]}",
            from_page_id=source_page.id,
            to_page_id=target_page.id,
            relation_type="merged_into",
            auto_generated=False,
        )
    )
    create_audit_log(
        db,
        action="merge_review",
        object_type="page",
        object_id=target_page.id,
        actor=actor,
        summary=f"Merged `{source_page.title}` into `{target_page.title}`",
        metadata={"reviewItemId": item_id, "sourcePageId": source_page.id, "targetPageId": target_page.id, "comment": comment, **(actor_metadata or {})},
    )
    create_audit_log(
        db,
        action="merged_into",
        object_type="page",
        object_id=source_page.id,
        actor=actor,
        summary=f"Archived after merge into `{target_page.title}`",
        metadata={"reviewItemId": item_id, "targetPageId": target_page.id, **(actor_metadata or {})},
    )
    source_page.status = "archived"
    source_page.last_reviewed_at = now
    source_page.related_page_ids = sorted(set(source_page.related_page_ids or []) | {target_page.id})

    if not item_id.startswith("virtual-"):
        persisted = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
        if persisted:
            db.delete(persisted)

    db.commit()
    return {
        "success": True,
        "mergedPage": get_page_by_slug(db, target_page.slug),
        "archivedPage": get_page_by_slug(db, source_page.slug),
        "targetPageId": target_page.id,
    }


def _unique_slug(db: Session, base: str) -> str:
    root = slugify(base) or f"issue-{uuid4().hex[:6]}"
    candidate = root
    suffix = 1
    while db.query(Page).filter(Page.slug == candidate).first():
        suffix += 1
        candidate = f"{root}-{suffix}"
    return candidate


def _issue_page_markdown(item: dict, source_page: Page | None) -> tuple[str, list[str]]:
    severity = item.get("severity", "medium")
    issue_type = str(item.get("issueType") or "issue").replace("_", " ")
    issues = item.get("issues") or []
    evidence_snippets = item.get("evidenceSnippets") or []
    source_title = source_page.title if source_page else item.get("pageTitle", "Unknown page")
    title = f"Issue: {source_title} - {issue_type.title()}"
    risk_lines = [
        f"- **Severity:** {severity}",
        f"- **Status:** open",
        f"- **Owner:** Knowledge Ops",
        f"- **Source page:** {source_title}",
    ]
    evidence_lines = []
    for issue in issues:
        evidence_lines.append(f"- **{issue.get('severity', severity)}:** {issue.get('message', '')} Evidence: {issue.get('evidence', '')}")
    for snippet in evidence_snippets:
        evidence_lines.append(f"- **{snippet.get('sourceTitle', 'Source')}**: {snippet.get('content', '')[:260]}")
    if not evidence_lines:
        evidence_lines.append("- Add source-backed evidence before closing this issue.")

    summary = f"{issue_type.title()} issue captured from the review workflow for {source_title}."
    lines = [
        f"# {title}",
        "",
        summary,
        "",
        "## Issue Summary",
        "",
        item.get("changeSummary") or summary,
        "",
        "## Risk And Impact",
        "",
        *risk_lines,
        "",
        "## Evidence",
        "",
        *evidence_lines,
        "",
        "## Resolution Plan",
        "",
        "- Validate the source evidence and impacted page content.",
        "- Update or merge the affected page if the issue is confirmed.",
        "- Re-run lint/review checks before publishing.",
    ]
    key_facts = [line.replace("- ", "", 1) for line in risk_lines[:3]]
    return "\n".join(lines).strip(), key_facts


def create_issue_page_from_review_item(db: Session, item_id: str) -> dict | None:
    item = get_review_item(db, item_id)
    if not item:
        return None

    source_page = db.query(Page).filter(Page.id == item["pageId"]).first()
    title = f"Issue: {item['pageTitle']} - {str(item['issueType']).replace('_', ' ').title()}"
    content_md, key_facts = _issue_page_markdown(item, source_page)
    summary = f"{str(item['issueType']).replace('_', ' ').title()} issue for {item['pageTitle']} with severity {item['severity']}."
    source_ids = item.get("sourceIds") or []
    collection_id = source_page.collection_id if source_page else None
    page = create_page_with_version(
        db,
        title=title,
        slug=_unique_slug(db, title),
        summary=summary,
        content_md=content_md,
        owner="Knowledge Ops",
        page_type="issue",
        status="draft",
        tags=sorted(set(["issue", str(item["issueType"]), str(item["severity"]), *build_tags(title, content_md)[:4]])),
        key_facts=key_facts,
        related_source_ids=source_ids,
        related_entity_ids=source_page.related_entity_ids if source_page else [],
        collection_id=collection_id,
    )
    if source_page:
        page.related_page_ids = sorted(set([source_page.id]))
        source_page.related_page_ids = sorted(set([*(source_page.related_page_ids or []), page.id]))
        db.add(
            PageLink(
                id=f"plink-issue-{uuid4().hex[:12]}",
                from_page_id=page.id,
                to_page_id=source_page.id,
                relation_type="issue_about",
                auto_generated=False,
            )
        )
        create_audit_log(
            db,
            action="create_issue_page",
            object_type="page",
            object_id=source_page.id,
            actor="Knowledge Ops",
            summary=f"Created issue page `{title}` from review workflow",
            metadata={"reviewItemId": item_id, "issuePageId": page.id},
        )
    db.commit()
    return {"success": True, "issuePage": get_page_by_slug(db, page.slug), "sourceReviewItemId": item_id}
