from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase41.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_comparison_conflict_sources(db) -> None:
    now = datetime.now(timezone.utc)
    source_a = Source(
        id="src-phase41-a",
        title="Global Access Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved", "documentType": "policy"},
        checksum="phase41-a",
        trust_level="high",
        file_size=None,
        description="Global policy",
        tags=["policy"],
        collection_id=None,
    )
    source_b = Source(
        id="src-phase41-b",
        title="Regional Access Note",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "informal", "sourceStatus": "draft", "documentType": "policy"},
        checksum="phase41-b",
        trust_level="medium",
        file_size=None,
        description="Regional note",
        tags=["note"],
        collection_id=None,
    )
    chunk_a = SourceChunk(
        id="chunk-phase41-a",
        source_id=source_a.id,
        chunk_index=0,
        section_title="Policy Rule",
        page_number=1,
        content="Global policy requires CAB approval for production changes affecting more than 5000 users.",
        token_count=13,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=92,
        created_at=now,
    )
    chunk_b = SourceChunk(
        id="chunk-phase41-b",
        source_id=source_b.id,
        chunk_index=0,
        section_title="Regional Note",
        page_number=1,
        content="Regional note says CAB approval is only needed above 3000 users for one local team.",
        token_count=15,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=84,
        created_at=now,
    )
    db.add_all([source_a, source_b, chunk_a, chunk_b])
    db.commit()


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_comparison_conflict_sources(db)

        comparison = ask(db, "Compare Global Access Policy and Regional Access Note for CAB approval threshold.")
        conflict = ask(db, "What conflict exists between Global Access Policy and Regional Access Note?")

        comparison_context = comparison.get("diagnostics", {}).get("selectedContext") or []
        conflict_context = conflict.get("diagnostics", {}).get("selectedContext") or []
        conflict_records = conflict.get("conflicts") or []

        payload = {
            "success": True,
            "comparisonRoles": [item.get("role") for item in comparison_context],
            "comparisonSources": [item.get("sourceId") for item in comparison_context if item.get("sourceId")],
            "conflictRoles": [item.get("role") for item in conflict_context],
            "conflictPreferredSource": (conflict_records or [{}])[0].get("preferredSourceTitle"),
        }

        checks = [
            "comparison_a" in payload["comparisonRoles"],
            "comparison_b" in payload["comparisonRoles"],
            len(set(payload["comparisonSources"])) >= 2,
            "conflict_side_a" in payload["conflictRoles"],
            "conflict_side_b" in payload["conflictRoles"],
            payload["conflictPreferredSource"] == "Global Access Policy",
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 41 comparison/conflict retrieval policy regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
