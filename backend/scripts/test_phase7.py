from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase7.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.lint import run_lint  # noqa: E402
from app.services.pages import get_page_by_slug, list_pages  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        page = get_page_by_slug(db, "llm-integration-standards")
        pages = list_pages(db, page_size=50)
        lint = run_lint(db, page_size=100, rule_id="missing_citation_map")
        citations = page.get("citations", []) if page else []
        first = citations[0] if citations else {}
        source_url = f"/sources/{first.get('sourceId')}?chunkId={first.get('chunkId')}" if first else None

        payload = {
            "success": True,
            "pageFound": bool(page),
            "citationCount": len(citations),
            "firstCitation": first,
            "sourceUrl": source_url,
            "listPagesHasCitations": any(item.get("citations") for item in pages.get("data", [])),
            "lintMissingCitationMapCount": lint.get("total"),
            "lintRuleRegistered": "missing_citation_map" in lint.get("summary", {}).get("byRule", {}),
        }

        required_keys = {
            "id",
            "claimId",
            "claimText",
            "sourceId",
            "sourceTitle",
            "chunkId",
            "chunkSectionTitle",
            "snippet",
            "sourceSpanStart",
            "sourceSpanEnd",
            "confidence",
        }
        checks = [
            payload["pageFound"],
            payload["citationCount"] >= 1,
            required_keys.issubset(first.keys()),
            bool(first.get("sourceId")),
            bool(first.get("chunkId")),
            payload["sourceUrl"] and "?chunkId=" in payload["sourceUrl"],
            payload["listPagesHasCitations"],
            isinstance(payload["lintMissingCitationMapCount"], int),
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 7 citation grounding checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
