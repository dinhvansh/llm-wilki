from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase42.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Page, PageSourceLink, Source  # noqa: E402
from app.services.lint import run_lint  # noqa: E402


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _page(page_id: str, title: str, status: str = "published") -> Page:
    now = _now()
    return Page(
        id=page_id,
        slug=page_id,
        title=title,
        page_type="summary",
        status=status,
        summary="Source authority validation page summary.",
        content_md=f"# {title}\n\nGrounded test content.",
        content_html=None,
        current_version=1,
        last_composed_at=now,
        last_reviewed_at=None,
        published_at=now if status == "published" else None,
        owner="test",
        tags=["test", "authority"],
        parent_page_id=None,
        key_facts=["Authority test fact"],
        related_page_ids=[],
        related_entity_ids=[],
        collection_id=None,
    )


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        page = _page("phase42-page", "Authority Mixed Page")
        official = Source(
            id="phase42-official",
            title="Official Access Policy",
            source_type="markdown",
            mime_type="text/markdown",
            file_path=None,
            url=None,
            uploaded_at=_now(),
            updated_at=_now(),
            created_by="test",
            parse_status="completed",
            ingest_status="completed",
            metadata_json={"authorityLevel": "official", "sourceStatus": "approved", "documentType": "policy"},
            checksum="phase42-official",
            trust_level="high",
            file_size=1,
            description="Official policy source",
            tags=["policy"],
            collection_id=None,
        )
        archived = Source(
            id="phase42-archived",
            title="Archived Access Note",
            source_type="markdown",
            mime_type="text/markdown",
            file_path=None,
            url=None,
            uploaded_at=_now() - timedelta(days=400),
            updated_at=_now() - timedelta(days=400),
            created_by="test",
            parse_status="completed",
            ingest_status="completed",
            metadata_json={"authorityLevel": "informal", "sourceStatus": "archived", "documentType": "meeting_note"},
            checksum="phase42-archived",
            trust_level="medium",
            file_size=1,
            description="Archived note",
            tags=["note"],
            collection_id=None,
        )
        links = [
            PageSourceLink(id="phase42-link-official", page_id=page.id, source_id=official.id),
            PageSourceLink(id="phase42-link-archived", page_id=page.id, source_id=archived.id),
        ]

        db.add_all([page, official, archived, *links])
        db.commit()

        result = run_lint(db, page_size=200)
        by_rule = result["summary"]["byRule"]
        issues = {
            item["ruleId"]: item
            for item in result["data"]
            if item["pageId"] == page.id and item["ruleId"] in {"authority_mismatch_sources", "archived_source_link"}
        }

        payload = {
            "success": True,
            "byRule": by_rule,
            "authorityIssueMetadata": issues.get("authority_mismatch_sources", {}).get("metadata"),
            "archivedIssueMetadata": issues.get("archived_source_link", {}).get("metadata"),
        }

        checks = [
            by_rule.get("authority_mismatch_sources", 0) >= 1,
            by_rule.get("archived_source_link", 0) >= 1,
            "phase42-official" in ((issues.get("authority_mismatch_sources", {}).get("metadata") or {}).get("authoritativeSourceIds") or []),
            "phase42-archived" in ((issues.get("authority_mismatch_sources", {}).get("metadata") or {}).get("weakerSourceIds") or []),
            "phase42-archived" in ((issues.get("archived_source_link", {}).get("metadata") or {}).get("sourceIds") or []),
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 42 authority/archive lint regression failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
