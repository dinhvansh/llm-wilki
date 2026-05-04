from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase8.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import PageSourceLink, Source  # noqa: E402
from app.services.suggestions import (  # noqa: E402
    accept_suggestion,
    accept_pending_suggestions,
    change_suggestion_target,
    create_source_suggestion,
    list_source_suggestions,
    reject_suggestion,
    reject_pending_suggestions,
    set_source_standalone,
)


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        source = db.query(Source).filter(Source.id == "src-001").first()
        source.collection_id = None
        collection_suggestion = create_source_suggestion(
            db,
            source_id="src-001",
            suggestion_type="collection_match",
            target_type="collection",
            target_id="col-002",
            target_label="Engineering Standards",
            confidence_score=0.8,
            reason="Test collection suggestion",
            evidence=[{"matchedTerms": ["llm"]}],
        )
        page_suggestion = create_source_suggestion(
            db,
            source_id="src-001",
            suggestion_type="page_match",
            target_type="page",
            target_id="page-002",
            target_label="LLM Integration Standards",
            confidence_score=0.7,
            reason="Test page suggestion",
            evidence=[{"matchedTerms": ["standards"]}],
        )
        rejectable = create_source_suggestion(
            db,
            source_id="src-001",
            suggestion_type="page_match",
            target_type="page",
            target_id="page-003",
            target_label="Source Processing Pipeline",
            confidence_score=0.6,
            reason="Test reject",
            evidence=[],
        )
        bulk_acceptable = create_source_suggestion(
            db,
            source_id="src-001",
            suggestion_type="entity_match",
            target_type="entity",
            target_id="ent-001",
            target_label="RAG",
            confidence_score=0.75,
            reason="Test bulk accept",
            evidence=[],
        )
        bulk_rejectable = create_source_suggestion(
            db,
            source_id="src-002",
            suggestion_type="page_match",
            target_type="page",
            target_id="page-001",
            target_label="AI Governance Policy",
            confidence_score=0.66,
            reason="Test bulk reject",
            evidence=[],
        )
        db.commit()

        changed = change_suggestion_target(db, page_suggestion.id, "page-001")
        accepted_collection = accept_suggestion(db, collection_suggestion.id)
        accepted_page = accept_suggestion(db, page_suggestion.id)
        rejected = reject_suggestion(db, rejectable.id)
        bulk_accepted = accept_pending_suggestions(db, "src-001")
        bulk_rejected = reject_pending_suggestions(db, "src-002")
        listed = list_source_suggestions(db, "src-001")
        standalone = set_source_standalone(db, "src-001")
        db.refresh(source)

        linked_page = (
            db.query(PageSourceLink)
            .filter(PageSourceLink.page_id == "page-001", PageSourceLink.source_id == "src-001")
            .first()
        )

        payload = {
            "success": True,
            "listedCount": len(listed),
            "changedTargetId": changed.get("targetId") if changed else None,
            "acceptedCollectionStatus": accepted_collection.get("status") if accepted_collection else None,
            "acceptedPageStatus": accepted_page.get("status") if accepted_page else None,
            "rejectedStatus": rejected.get("status") if rejected else None,
            "bulkAcceptedCount": bulk_accepted.get("acceptedCount") if bulk_accepted else None,
            "bulkRejectedCount": bulk_rejected.get("rejectedCount") if bulk_rejected else None,
            "pageLinked": bool(linked_page),
            "standalone": standalone,
            "sourceCollectionId": source.collection_id,
        }
        checks = [
            payload["listedCount"] >= 3,
            payload["changedTargetId"] == "page-001",
            payload["acceptedCollectionStatus"] == "accepted",
            payload["acceptedPageStatus"] == "accepted",
            payload["rejectedStatus"] == "rejected",
            payload["bulkAcceptedCount"] >= 1,
            payload["bulkRejectedCount"] == 1,
            payload["pageLinked"],
            payload["standalone"] == {"sourceId": "src-001", "collectionId": None},
            payload["sourceCollectionId"] is None,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 8 suggestion workflow checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
