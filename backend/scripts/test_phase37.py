from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase37.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import KnowledgeUnit, Source  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_knowledge_unit_source(db) -> None:
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-phase37-policy",
        title="Production Change Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"documentType": "policy", "authorityLevel": "official", "sourceStatus": "approved"},
        checksum="src-phase37-policy",
        trust_level="high",
        file_size=None,
        description="Policy for production changes.",
        tags=["policy", "change"],
        collection_id=None,
    )
    unit = KnowledgeUnit(
        id="ku-phase37-threshold",
        source_id=source.id,
        source_chunk_id=None,
        claim_id=None,
        unit_type="threshold",
        title="Production freeze threshold",
        text="Changes affecting more than 5000 users require CAB approval before deployment.",
        status="draft",
        review_status="approved",
        canonical_status="verified",
        confidence_score=0.91,
        topic="Approval threshold",
        entity_ids=[],
        evidence_span_start=None,
        evidence_span_end=None,
        metadata_json={"documentType": "policy", "authorityLevel": "official"},
        created_at=now,
        updated_at=now,
    )
    db.add_all([source, unit])
    db.commit()


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_knowledge_unit_source(db)
        answer = ask(db, "What threshold requires CAB approval before deployment?")
        diagnostics = answer.get("diagnostics") or {}
        top_candidates = diagnostics.get("topCandidates") or []
        selected_context = diagnostics.get("selectedContext") or []

        payload = {
            "success": True,
            "topCandidateTypes": [item.get("candidateType") for item in top_candidates[:5]],
            "selectedContextTypes": [item.get("candidateType") for item in selected_context[:5]],
            "hasKnowledgeUnitTopCandidate": any(item.get("candidateType") == "knowledge_unit" for item in top_candidates),
            "hasKnowledgeUnitContext": any(item.get("candidateType") == "knowledge_unit" for item in selected_context),
        }

        checks = [
            payload["hasKnowledgeUnitTopCandidate"] is True,
            payload["hasKnowledgeUnitContext"] is True,
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 37 knowledge unit retrieval regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
