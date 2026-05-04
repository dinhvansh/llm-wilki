from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase11.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Page, PageSourceLink, ReviewIssue, ReviewItem, Source  # noqa: E402
from app.services.lint import run_lint  # noqa: E402


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _page(page_id: str, title: str, page_type: str = "summary", status: str = "draft", content: str | None = None) -> Page:
    return Page(
        id=page_id,
        slug=page_id,
        title=title,
        page_type=page_type,
        status=status,
        summary="Short summary",
        content_md=content or f"# {title}\n\nMinimal test page.",
        content_html=None,
        current_version=1,
        last_composed_at=_now(),
        last_reviewed_at=None,
        published_at=_now() if status == "published" else None,
        owner="test",
        tags=["test", page_type],
        parent_page_id=None,
        key_facts=["Test fact"],
        related_page_ids=[],
        related_entity_ids=[],
        collection_id=None,
    )


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        duplicate_a = _page("phase11-duplicate-a", "Duplicate Knowledge")
        duplicate_b = _page("phase11-duplicate-b", "Duplicate Knowledge")
        published_no_source = _page("phase11-published-no-source", "Published Unsupported", status="published")
        timeline = _page("phase11-timeline", "Sparse Timeline", page_type="timeline", content="# Sparse Timeline\n\n## Timeline\n\nNo structured milestones yet.")
        issue = _page("phase11-issue", "Unowned Issue", page_type="issue", content="# Unowned Issue\n\n## Issue\n\n**Owner:** TBD\n\n**Status:** TBD")
        conflict_page = _page("phase11-conflict", "Conflict Target")
        stale_page = _page("phase11-stale-source-page", "Stale Source Page", status="published")
        stale_source = Source(
            id="phase11-stale-source",
            title="Old Authoritative Source",
            source_type="pdf",
            mime_type="application/pdf",
            file_path=None,
            url=None,
            uploaded_at=_now() - timedelta(days=420),
            updated_at=_now() - timedelta(days=420),
            created_by="test",
            parse_status="parsed",
            ingest_status="completed",
            metadata_json={},
            checksum="phase11-stale-source",
            trust_level="authoritative",
            file_size=1,
            description="Old source",
            tags=["test"],
            collection_id=None,
        )
        stale_link = PageSourceLink(id="phase11-stale-link", page_id=stale_page.id, source_id=stale_source.id)
        review_item = ReviewItem(
            id="phase11-review-conflict",
            page_id=conflict_page.id,
            page_title=conflict_page.title,
            page_slug=conflict_page.slug,
            page_status=conflict_page.status,
            issue_type="conflict",
            severity="high",
            old_content_md="old",
            new_content_md="new",
            change_summary="Conflict evidence",
            confidence_score=0.91,
            created_at=_now(),
            updated_at=_now(),
            assigned_to=None,
            previous_version=None,
            source_ids=[],
            evidence_snippets=[],
        )
        review_issue = ReviewIssue(
            id="phase11-review-issue",
            review_item_id=review_item.id,
            issue_type="conflict",
            severity="high",
            message="Contradictory claims detected",
            evidence="Synthetic test conflict",
            source_chunk_id=None,
            claim_id=None,
        )

        db.add_all([
            duplicate_a,
            duplicate_b,
            published_no_source,
            timeline,
            issue,
            conflict_page,
            stale_page,
            stale_source,
            stale_link,
            review_item,
            review_issue,
        ])
        db.commit()

        result = run_lint(db, page_size=500)
        by_rule = result["summary"]["byRule"]
        quick_fix_count = sum(1 for item in result["data"] if item["metadata"].get("quickFix"))
        page_type_filter = run_lint(db, page_type="issue", page_size=500)
        rule_filter = run_lint(db, rule_id="duplicate_pages", page_size=500)

        expected_rules = [
            "duplicate_pages",
            "entity_without_page",
            "published_source_coverage",
            "timeline_missing_key_milestones",
            "issue_missing_owner_status",
            "conflicting_pages",
            "stale_authoritative_source",
        ]
        payload = {
            "success": True,
            "byRule": by_rule,
            "quickFixCount": quick_fix_count,
            "issueFilterCount": page_type_filter["total"],
            "duplicateFilterCount": rule_filter["total"],
        }
        checks = [
            all(by_rule.get(rule, 0) > 0 for rule in expected_rules),
            quick_fix_count >= len(expected_rules),
            page_type_filter["total"] >= 1,
            rule_filter["total"] >= 2,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 11 lint expansion checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
