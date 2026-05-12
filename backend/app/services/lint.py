from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Entity, Page, PageClaimLink, PageLink, PageSourceLink, ReviewIssue, ReviewItem, Source, TimelineEvent
from app.core.ingest import build_tags
from app.services.audit import create_audit_log
from app.services.pages import _page_backlinks_map, _page_source_map
from app.services.pages import create_page_with_version, update_page_content


WORD_RE = re.compile(r"\b[\w-]+\b")


def _severity_rank(value: str) -> int:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return order.get(value, 0)


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lstrip("#").strip()).lower()


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").strip().lower()).strip()


def _months_since(value: datetime | None) -> int | None:
    if not value:
        return None
    now = datetime.now(timezone.utc)
    compared = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (now.year - compared.year) * 12 + now.month - compared.month)


def _source_authority_level(source: Source) -> str:
    metadata = source.metadata_json or {}
    return str(metadata.get("authorityLevel") or metadata.get("authority_level") or "").strip().lower()


def _source_status(source: Source) -> str:
    metadata = source.metadata_json or {}
    return str(metadata.get("sourceStatus") or metadata.get("source_status") or "").strip().lower()


def _lint_issue(page: Page, rule_id: str, severity: str, title: str, message: str, suggestion: str, metadata: dict | None = None) -> dict:
    issue_metadata = {
        "collectionId": page.collection_id,
        **(metadata or {}),
    }
    return {
        "id": f"lint-{rule_id}-{page.id}",
        "pageId": page.id,
        "pageSlug": page.slug,
        "pageTitle": page.title,
        "pageStatus": page.status,
        "pageType": page.page_type,
        "ruleId": rule_id,
        "severity": severity,
        "title": title,
        "message": message,
        "suggestion": suggestion,
        "metadata": issue_metadata,
    }


def _quick_fix(action: str, label: str, payload: dict | None = None) -> dict:
    return {"quickFix": {"action": action, "label": label, "payload": payload or {}}}


def _run_rules(
    page: Page,
    source_ids: list[str],
    linked_sources: list[Source],
    backlinks: list[dict],
    page_ids: set[str],
    citation_count: int,
    duplicate_titles: dict[str, list[str]],
    timeline_event_counts: dict[str, int],
    conflict_page_ids: set[str],
    stale_source_ids: set[str],
) -> list[dict]:
    issues: list[dict] = []
    content = page.content_md or ""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    first_heading = next((line for line in lines if line.startswith("#")), "")
    summary_words = _word_count(page.summary)
    content_words = _word_count(content)
    key_facts = page.key_facts or []
    related_page_ids = page.related_page_ids or []
    tags = page.tags or []

    if not first_heading:
        issues.append(
            _lint_issue(
                page,
                "missing_primary_heading",
                "medium",
                "Missing primary heading",
                "Page content does not start with a Markdown heading.",
                "Add a top-level `# Heading` that matches the page title.",
            )
        )
    elif _normalize_heading(first_heading) != _normalize_heading(page.title):
        issues.append(
            _lint_issue(
                page,
                "title_heading_mismatch",
                "medium",
                "Title and heading mismatch",
                f"First heading is `{first_heading}` but page title is `{page.title}`.",
                "Align the first heading with the canonical page title.",
            )
        )

    normalized_title = _normalize_title(page.title)
    duplicate_page_ids = [page_id for page_id in duplicate_titles.get(normalized_title, []) if page_id != page.id]
    if duplicate_page_ids:
        issues.append(
            _lint_issue(
                page,
                "duplicate_pages",
                "high",
                "Possible duplicate page",
                f"Page title overlaps with {len(duplicate_page_ids)} other page(s).",
                "Review overlapping pages and merge, rename, or mark the relationship explicitly.",
                {
                    "duplicatePageIds": duplicate_page_ids,
                    **_quick_fix("review_duplicates", "Review duplicate candidates", {"pageId": page.id, "duplicatePageIds": duplicate_page_ids}),
                },
            )
        )

    if not source_ids:
        issues.append(
            _lint_issue(
                page,
                "missing_source_links",
                "high",
                "No linked sources",
                "Page is not linked to any source record.",
                "Attach at least one source or mark the page as intentionally synthetic.",
                _quick_fix("attach_source", "Attach source", {"pageId": page.id}),
            )
        )
    elif citation_count == 0 and (key_facts or page.status in {"in_review", "published"}):
        issues.append(
            _lint_issue(
                page,
                "missing_citation_map",
                "high",
                "No claim-to-source citations",
                "Page is linked to source records but has no page claim links for chunk-level citation tracing.",
                "Link page claims to source chunks so readers can trace facts back to source evidence.",
                {
                    "sourceIds": source_ids,
                    "citationCount": citation_count,
                    **_quick_fix("generate_citations", "Generate citation map", {"pageId": page.id, "sourceIds": source_ids}),
                },
            )
        )

    if page.status == "published" and len(source_ids) < 1:
        issues.append(
            _lint_issue(
                page,
                "published_source_coverage",
                "critical",
                "Published page lacks source coverage",
                "Published pages must have at least one linked source.",
                "Attach authoritative source evidence before keeping this page published.",
                _quick_fix("attach_source", "Attach source evidence", {"pageId": page.id}),
            )
        )

    stale_linked_sources = [source_id for source_id in source_ids if source_id in stale_source_ids]
    if stale_linked_sources and page.status in {"published", "in_review"}:
        issues.append(
            _lint_issue(
                page,
                "stale_authoritative_source",
                "high",
                "Linked authoritative source is stale",
                f"{len(stale_linked_sources)} linked authoritative source(s) are older than the freshness threshold.",
                "Refresh, replace, or explicitly approve the stale source evidence.",
                {
                    "sourceIds": stale_linked_sources,
                    **_quick_fix("request_rebuild", "Refresh stale sources", {"sourceIds": stale_linked_sources}),
                },
            )
        )

    authoritative_sources = [
        source
        for source in linked_sources
        if _source_authority_level(source) == "official" or _source_status(source) in {"approved", "published"}
    ]
    weak_sources = [
        source
        for source in linked_sources
        if _source_authority_level(source) in {"informal", "user_note"} or _source_status(source) in {"draft", "archived"}
    ]
    archived_sources = [source for source in linked_sources if _source_status(source) == "archived"]

    if authoritative_sources and weak_sources:
        issues.append(
            _lint_issue(
                page,
                "authority_mismatch_sources",
                "high" if page.status in {"published", "in_review"} else "medium",
                "Page mixes authoritative and weak sources",
                "This page links both authoritative/approved evidence and weaker draft/informal evidence.",
                "Review citations and either remove weak evidence, downgrade the page, or document why mixed authority is acceptable.",
                {
                    "authoritativeSourceIds": [source.id for source in authoritative_sources],
                    "weakerSourceIds": [source.id for source in weak_sources],
                    "authoritativeTitles": [source.title for source in authoritative_sources],
                    "weakerTitles": [source.title for source in weak_sources],
                },
            )
        )

    if archived_sources and page.status in {"published", "in_review"}:
        issues.append(
            _lint_issue(
                page,
                "archived_source_link",
                "high",
                "Page links archived source evidence",
                "Archived sources should not remain primary evidence for published or in-review pages.",
                "Refresh the page with current evidence or explicitly demote/remove archived source links.",
                {
                    "sourceIds": [source.id for source in archived_sources],
                    "sourceTitles": [source.title for source in archived_sources],
                },
            )
        )

    if summary_words < 12:
        issues.append(
            _lint_issue(
                page,
                "thin_summary",
                "medium",
                "Summary is too thin",
                f"Page summary has only {summary_words} words.",
                "Expand the summary to capture scope, audience, and key outcome.",
                {"wordCount": summary_words},
            )
        )

    if not key_facts:
        issues.append(
            _lint_issue(
                page,
                "missing_key_facts",
                "medium",
                "Key facts missing",
                "Page does not expose any key facts.",
                "Add 2-5 concise key facts for skim reading and graph/linking.",
            )
        )

    broken_related_pages = [related_id for related_id in related_page_ids if related_id not in page_ids]
    if broken_related_pages:
        issues.append(
            _lint_issue(
                page,
                "broken_related_page",
                "high",
                "Broken related page references",
                f"Page references {len(broken_related_pages)} related pages that do not exist.",
                "Remove stale related-page ids or recreate the missing pages.",
                {"brokenPageIds": broken_related_pages},
            )
        )

    if not backlinks and not related_page_ids and content_words > 80:
        issues.append(
            _lint_issue(
                page,
                "isolated_page",
                "low",
                "Page is isolated",
                "Page has no backlinks and no related page references.",
                "Link the page from a hub page or add related pages for discovery.",
                {"contentWords": content_words},
            )
        )

    if len(tags) < 2:
        issues.append(
            _lint_issue(
                page,
                "sparse_tags",
                "low",
                "Tags are sparse",
                f"Page currently has {len(tags)} tags.",
                "Add a few high-signal tags to improve filtering and navigation.",
                {"tagCount": len(tags)},
            )
        )

    if page.page_type == "sop" and not re.search(r"##\s+(Procedure|Steps|Validation Checklist)|###\s+Step\s+\d+", content, flags=re.IGNORECASE):
        issues.append(
            _lint_issue(
                page,
                "sop_missing_steps",
                "high",
                "SOP is missing structured steps",
                "SOP pages should expose procedure steps and validation checks.",
                "Add a `## Procedure` section with numbered steps and a validation checklist.",
            )
        )

    if page.page_type == "timeline" and not re.search(r"##\s+Timeline|\*\*\d{4}|Q[1-4]\s+\d{4}", content, flags=re.IGNORECASE):
        issues.append(
            _lint_issue(
                page,
                "timeline_missing_events",
                "high",
                "Timeline is missing events",
                "Timeline pages should expose dated milestones or events.",
                "Add a `## Timeline` section with dated events sourced from evidence.",
            )
        )
    elif page.page_type == "timeline" and timeline_event_counts.get(page.id, 0) < 2:
        issues.append(
            _lint_issue(
                page,
                "timeline_missing_key_milestones",
                "medium",
                "Timeline has too few milestones",
                f"Timeline page has {timeline_event_counts.get(page.id, 0)} structured event(s).",
                "Add key milestones from source evidence so the timeline is useful for review.",
                {
                    "eventCount": timeline_event_counts.get(page.id, 0),
                    **_quick_fix("extract_timeline", "Extract timeline milestones", {"pageId": page.id}),
                },
            )
        )

    if page.page_type == "glossary" and not re.search(r"##\s+Glossary Terms|\*\*[^*]+\*\*:", content, flags=re.IGNORECASE):
        issues.append(
            _lint_issue(
                page,
                "glossary_missing_terms",
                "medium",
                "Glossary is missing term definitions",
                "Glossary pages should expose term-definition entries.",
                "Add a `## Glossary Terms` section with `Term: definition` entries.",
            )
        )

    if page.page_type == "entity" and not re.search(r"##\s+Entity Profile|\*\*Name:\*\*|\*\*Type:\*\*", content, flags=re.IGNORECASE):
        issues.append(
            _lint_issue(
                page,
                "entity_missing_profile",
                "medium",
                "Entity page is missing profile fields",
                "Entity pages should expose name, type, description, and related entities/sources.",
                "Add an `## Entity Profile` section with key profile fields.",
            )
        )

    if page.page_type == "issue":
        missing_fields = []
        if not re.search(r"\*\*Owner:\*\*\s*(?!TBD|Unknown|Unassigned)\S+", content, flags=re.IGNORECASE):
            missing_fields.append("owner")
        if not re.search(r"\*\*Status:\*\*\s*(?!TBD|Unknown)\S+", content, flags=re.IGNORECASE):
            missing_fields.append("status")
        if missing_fields:
            issues.append(
                _lint_issue(
                    page,
                    "issue_missing_owner_status",
                    "high",
                    "Issue page is missing owner/status",
                    f"Issue page is missing required field(s): {', '.join(missing_fields)}.",
                    "Assign an owner and lifecycle status so the issue can be tracked.",
                    {
                        "missingFields": missing_fields,
                        **_quick_fix("edit_issue_fields", "Fill issue owner/status", {"pageId": page.id, "missingFields": missing_fields}),
                    },
                )
            )

    if page.id in conflict_page_ids:
        issues.append(
            _lint_issue(
                page,
                "conflicting_pages",
                "high",
                "Page has unresolved conflict signals",
                "Review queue contains conflict evidence for this page.",
                "Resolve or document the conflict before publishing or relying on this page.",
                _quick_fix("open_review_queue", "Open conflict review", {"pageId": page.id}),
            )
        )

    return issues


def _entity_page_ids(db: Session) -> set[str]:
    return {
        page_id
        for (page_id,) in db.query(Page.id).filter(Page.page_type == "entity").all()
    }


def run_lint(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    severity: str | None = None,
    rule_id: str | None = None,
    search: str | None = None,
    page_type: str | None = None,
    collection_id: str | None = None,
    max_pages: int = 500,
) -> dict:
    scan_limit = max(1, min(max_pages, 5000))
    pages = db.query(Page).order_by(Page.last_composed_at.desc()).limit(scan_limit).all()
    if page_type:
        pages = [item for item in pages if item.page_type == page_type]
    if collection_id:
        pages = [item for item in pages if (item.collection_id or "standalone") == collection_id]
    page_ids = {item.id for item in pages}
    source_map = _page_source_map(db, [item.id for item in pages])
    source_lookup = {source.id: source for source in db.query(Source).all()}
    backlinks_map = _page_backlinks_map(db, [item.id for item in pages])
    all_pages = db.query(Page).all()
    duplicate_title_counts: dict[str, list[str]] = {}
    for item in all_pages:
        normalized = _normalize_title(item.title)
        if normalized:
            duplicate_title_counts.setdefault(normalized, []).append(item.id)
    duplicate_titles = {title: ids for title, ids in duplicate_title_counts.items() if len(ids) > 1}
    timeline_event_counts = Counter(
        page_id
        for (page_id,) in db.query(TimelineEvent.page_id).filter(TimelineEvent.page_id.in_([item.id for item in pages])).all()
        if page_id
    )
    conflict_page_ids = {
        page_id
        for (page_id,) in (
            db.query(ReviewItem.page_id)
            .join(ReviewIssue, ReviewIssue.review_item_id == ReviewItem.id)
            .filter(ReviewIssue.issue_type.in_(["conflict", "claim_conflict", "contradiction"]))
            .all()
        )
    }
    conflict_page_ids.update(
        page_id
        for (page_id,) in db.query(Page.id).filter(Page.page_type == "issue", Page.content_md.ilike("%conflict%")).all()
    )
    all_sources = list(source_lookup.values())
    stale_source_ids = {
        source.id
        for source in all_sources
        if source.trust_level in {"high", "authoritative", "trusted"} and (_months_since(source.updated_at) or 0) >= 6
    }
    citation_counts = Counter(
        page_id
        for (page_id,) in db.query(PageClaimLink.page_id).filter(PageClaimLink.page_id.in_([item.id for item in pages])).all()
    )

    issues: list[dict] = []
    for item in pages:
        issues.extend(
            _run_rules(
                item,
                source_map.get(item.id, []),
                [source_lookup[source_id] for source_id in source_map.get(item.id, []) if source_id in source_lookup],
                backlinks_map.get(item.id, []),
                page_ids,
                citation_counts.get(item.id, 0),
                duplicate_titles,
                timeline_event_counts,
                conflict_page_ids,
                stale_source_ids,
            )
        )

    if not collection_id and (not page_type or page_type == "entity"):
        linked_entity_ids = {
            entity_id
            for (entity_id,) in db.query(Entity.id).join(Entity.page_links).all()
        }
        page_entity_names = {_normalize_title(item.title) for item in db.query(Page).filter(Page.page_type == "entity").all()}
        for entity in db.query(Entity).all():
            if entity.id in linked_entity_ids or _normalize_title(entity.name) in page_entity_names:
                continue
            synthetic_page = Page(
                id=f"entity-{entity.id}",
                slug=f"entity-{entity.normalized_name}",
                title=entity.name,
                page_type="entity",
                status="draft",
                summary=entity.description or "",
                content_md="",
                owner="system",
                collection_id=None,
            )
            issues.append(
                _lint_issue(
                    synthetic_page,
                    "entity_without_page",
                    "medium",
                    "Entity has no page",
                    f"Entity `{entity.name}` is linked from sources but has no dedicated entity page.",
                    "Create or link an entity page so the graph has a canonical knowledge object.",
                    {
                        "entityId": entity.id,
                        "entityType": entity.entity_type,
                        **_quick_fix("create_entity_page", "Create entity page", {"entityId": entity.id}),
                    },
                )
            )

    if severity:
        issues = [item for item in issues if item["severity"] == severity]
    if rule_id:
        issues = [item for item in issues if item["ruleId"] == rule_id]
    if search:
        term = search.strip().lower()
        issues = [
            item
            for item in issues
            if term in item["pageTitle"].lower()
            or term in item["title"].lower()
            or term in item["message"].lower()
            or term in item["ruleId"].lower()
        ]

    issues.sort(key=lambda item: (-_severity_rank(item["severity"]), item["pageTitle"].lower(), item["ruleId"]))
    start = (page - 1) * page_size
    paged = issues[start : start + page_size]

    by_rule = Counter(item["ruleId"] for item in issues)
    by_severity = Counter(item["severity"] for item in issues)
    affected_pages = len({item["pageId"] for item in issues})

    return {
        "data": paged,
        "total": len(issues),
        "page": page,
        "pageSize": page_size,
        "hasMore": start + page_size < len(issues),
        "summary": {
            "issueCount": len(issues),
            "affectedPages": affected_pages,
            "scannedPages": len(pages),
            "scanLimit": max_pages,
            "byRule": dict(sorted(by_rule.items())),
            "bySeverity": dict(sorted(by_severity.items())),
            "rules": [
                {"id": "missing_primary_heading", "label": "Missing primary heading"},
                {"id": "title_heading_mismatch", "label": "Title heading mismatch"},
                {"id": "duplicate_pages", "label": "Duplicate pages"},
                {"id": "entity_without_page", "label": "Entity without page"},
                {"id": "missing_source_links", "label": "Missing source links"},
                {"id": "published_source_coverage", "label": "Published source coverage"},
                {"id": "stale_authoritative_source", "label": "Stale authoritative source"},
                {"id": "authority_mismatch_sources", "label": "Authority mismatch sources"},
                {"id": "archived_source_link", "label": "Archived source link"},
                {"id": "missing_citation_map", "label": "Missing citation map"},
                {"id": "conflicting_pages", "label": "Conflicting pages"},
                {"id": "thin_summary", "label": "Thin summary"},
                {"id": "missing_key_facts", "label": "Missing key facts"},
                {"id": "broken_related_page", "label": "Broken related page"},
                {"id": "isolated_page", "label": "Isolated page"},
                {"id": "sparse_tags", "label": "Sparse tags"},
                {"id": "sop_missing_steps", "label": "SOP missing steps"},
                {"id": "timeline_missing_events", "label": "Timeline missing events"},
                {"id": "timeline_missing_key_milestones", "label": "Timeline missing milestones"},
                {"id": "glossary_missing_terms", "label": "Glossary missing terms"},
                {"id": "entity_missing_profile", "label": "Entity missing profile"},
                {"id": "issue_missing_owner_status", "label": "Issue owner/status"},
            ],
        },
    }


def execute_lint_quick_fix(db: Session, action: str, payload: dict, actor: str = "Current User") -> dict:
    if action == "edit_issue_fields":
        page = db.query(Page).filter(Page.id == payload.get("pageId"), Page.page_type == "issue").first()
        if not page:
            return {"success": False, "message": "Issue page not found"}
        content = page.content_md or ""
        if "**Owner:**" not in content:
            content += "\n\n- **Owner:** Knowledge Ops"
        else:
            content = re.sub(r"\*\*Owner:\*\*\s*(TBD|Unknown|Unassigned)?", "**Owner:** Knowledge Ops", content, flags=re.IGNORECASE)
        if "**Status:**" not in content:
            content += "\n- **Status:** open"
        else:
            content = re.sub(r"\*\*Status:\*\*\s*(TBD|Unknown)?", "**Status:** open", content, flags=re.IGNORECASE)
        update_page_content(db, page.id, content, "Applied lint quick fix: issue fields", author=actor, expected_version=page.current_version)
        return {"success": True, "action": action, "pageId": page.id}

    if action == "create_entity_page":
        entity = db.query(Entity).filter(Entity.id == payload.get("entityId")).first()
        if not entity:
            return {"success": False, "message": "Entity not found"}
        existing = db.query(Page).filter(Page.page_type == "entity", Page.title == entity.name).first()
        if existing:
            return {"success": True, "action": action, "pageId": existing.id, "created": False}
        title = entity.name
        slug_root = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or f"entity-{entity.id}"
        slug = slug_root
        suffix = 1
        while db.query(Page).filter(Page.slug == slug).first():
            suffix += 1
            slug = f"{slug_root}-{suffix}"
        content = "\n".join(
            [
                f"# {title}",
                "",
                "## Entity Profile",
                "",
                f"- **Name:** {entity.name}",
                f"- **Type:** {entity.entity_type}",
                f"- **Description:** {entity.description or 'Add source-backed description.'}",
                f"- **Aliases:** {', '.join(entity.aliases or []) or 'None'}",
            ]
        )
        page = create_page_with_version(
            db,
            title=title,
            slug=slug,
            summary=entity.description or f"Entity profile for {entity.name}.",
            content_md=content,
            owner=actor,
            page_type="entity",
            status="draft",
            tags=build_tags(title, content),
            key_facts=[f"Type: {entity.entity_type}"],
            related_source_ids=[],
            related_entity_ids=[entity.id],
        )
        create_audit_log(db, action="lint_quick_fix", object_type="page", object_id=page.id, actor=actor, summary=f"Created entity page `{title}`", metadata={"quickFix": action, "entityId": entity.id})
        db.commit()
        return {"success": True, "action": action, "pageId": page.id, "created": True}

    return {"success": False, "message": f"Unsupported quick fix action `{action}`"}
