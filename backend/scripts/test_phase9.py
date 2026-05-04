from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase9.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.ingest import build_page_markdown  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.lint import run_lint  # noqa: E402
from app.services.pages import list_pages  # noqa: E402
from app.services.review import create_issue_page_from_review_item, list_review_items  # noqa: E402
from app.services.sources import create_source_record, ingest_source  # noqa: E402


SOURCE_TEXT = """
# Operational RAG Rollout Procedure

Step 1: The AI Platform team reviews retrieval configuration and confirms BM25 plus vector search.
Step 2: The reviewer validates citations, source chunks, and graph links before publishing.

RAG: Retrieval augmented generation that grounds answers in indexed source evidence.
BM25: A lexical retrieval algorithm used as the sparse side of hybrid search.
Citation Map: A page-to-claim-to-source-chunk link used for auditability.

In Q1 2026, the platform team launched the hybrid retrieval pilot.
In Q2 2026, the governance team required citation traceability for published pages.

The RAG System is the primary technology referenced by this operating procedure.
"""


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        source, _ = create_source_record(
            db,
            filename="operational-rag-rollout-procedure.txt",
            mime_type="text/plain",
            file_size=len(SOURCE_TEXT.encode("utf-8")),
            file_bytes=SOURCE_TEXT.encode("utf-8"),
        )
        result = ingest_source(db, source.id)
        pages = list_pages(db, page_size=200)
        review_items = list_review_items(db, page_size=50)
        review_item_id = review_items["data"][0]["id"] if review_items["data"] else None
        issue_result = create_issue_page_from_review_item(db, review_item_id) if review_item_id else None
        issue_page = issue_result.get("issuePage") if issue_result else None
        pages_after_issue = list_pages(db, page_size=250)
        generated = [page for page in pages["data"] if source.id in page.get("relatedSourceIds", [])]
        page_types = sorted({page["pageType"] for page in generated})
        content_by_type = {page["pageType"]: page["contentMd"] for page in generated}
        lint_rules = {rule["id"] for rule in run_lint(db, page_size=1)["summary"]["rules"]}

        template_samples = {
            "sop": build_page_markdown("SOP", "Summary", [], ["Fact"], page_type="sop"),
            "timeline": build_page_markdown(
                "Timeline",
                "Summary",
                [],
                [],
                page_type="timeline",
                timeline_events=[{"event_date": "Q1 2026", "title": "Pilot launched"}],
            ),
            "glossary": build_page_markdown(
                "Glossary",
                "Summary",
                [],
                [],
                page_type="glossary",
                glossary_terms=[{"term": "RAG", "definition": "Retrieval augmented generation.", "aliases": []}],
            ),
            "entity": build_page_markdown(
                "RAG System",
                "Summary",
                [],
                [],
                page_type="entity",
                entities=[{"name": "RAG System", "entity_type": "technology", "description": "Primary retrieval system."}],
            ),
        }

        payload = {
            "success": True,
            "ingestStatus": result.get("ingestStatus") if result else None,
            "generatedPageCount": len(generated),
            "pageTypes": page_types,
            "hasSopTemplate": "## Procedure" in template_samples["sop"],
            "hasTimelineTemplate": "## Timeline" in template_samples["timeline"],
            "hasGlossaryTemplate": "## Glossary Terms" in template_samples["glossary"],
            "hasEntityTemplate": "## Entity Profile" in template_samples["entity"],
            "generatedHasTimeline": any("## Timeline" in content for content in content_by_type.values()),
            "generatedHasGlossary": any("## Glossary Terms" in content for content in content_by_type.values()),
            "generatedHasEntity": any("## Entity Profile" in content for content in content_by_type.values()),
            "issuePageCreated": bool(issue_page),
            "issuePageType": issue_page.get("pageType") if issue_page else None,
            "issueHasRiskEvidence": bool(issue_page and "## Risk And Impact" in issue_page.get("contentMd", "") and "## Evidence" in issue_page.get("contentMd", "")),
            "issueInPages": bool(issue_page and any(page["id"] == issue_page["id"] for page in pages_after_issue["data"])),
            "lintRulesPresent": {"sop_missing_steps", "timeline_missing_events", "glossary_missing_terms", "entity_missing_profile"}.issubset(lint_rules),
        }
        checks = [
            payload["ingestStatus"] == "indexed",
            payload["generatedPageCount"] >= 3,
            payload["hasSopTemplate"],
            payload["hasTimelineTemplate"],
            payload["hasGlossaryTemplate"],
            payload["hasEntityTemplate"],
            payload["generatedHasTimeline"],
            payload["generatedHasGlossary"],
            payload["generatedHasEntity"],
            payload["issuePageCreated"],
            payload["issuePageType"] == "issue",
            payload["issueHasRiskEvidence"],
            payload["issueInPages"],
            payload["lintRulesPresent"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 9 structured template checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
