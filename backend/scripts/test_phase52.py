from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase52.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(ROOT))

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_data(db) -> None:
    now = datetime.now(timezone.utc)
    source_a = Source(
        id="src-phase52-policy",
        title="Global Approval Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "documentType": "policy",
            "authorityLevel": "official",
            "sourceStatus": "approved",
            "effectiveDate": "2026-05-01",
            "version": "2026.05",
        },
        checksum="phase52-policy",
        trust_level="high",
        file_size=None,
        description="Official global rule",
        tags=["policy"],
        collection_id=None,
    )
    source_b = Source(
        id="src-phase52-note",
        title="Regional Approval Note",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "documentType": "meeting_note",
            "authorityLevel": "informal",
            "sourceStatus": "draft",
            "effectiveDate": "2026-04-10",
            "version": "draft-2",
        },
        checksum="phase52-note",
        trust_level="medium",
        file_size=None,
        description="Regional note with weaker guidance",
        tags=["note"],
        collection_id=None,
    )
    db.add_all(
        [
            source_a,
            source_b,
            SourceChunk(
                id="chunk-phase52-policy",
                source_id=source_a.id,
                chunk_index=0,
                section_title="Approval Threshold",
                page_number=1,
                content="CAB approval is required for production changes affecting more than 5000 users.",
                token_count=12,
                embedding_id=None,
                metadata_json={"sectionRole": "rule"},
                span_start=0,
                span_end=84,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-phase52-note",
                source_id=source_b.id,
                chunk_index=0,
                section_title="Local Variation",
                page_number=1,
                content="A regional meeting note suggests CAB approval can be skipped below 3000 users.",
                token_count=14,
                embedding_id=None,
                metadata_json={"sectionRole": "rule"},
                span_start=0,
                span_end=82,
                created_at=now,
            ),
        ]
    )
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_data(db)
        response = ask(db, "What conflict exists between Global Approval Policy and Regional Approval Note?")
        answer = response.get("answer") or ""
        payload = {
            "success": True,
            "answerType": response.get("answerType"),
            "hasWhy": "## Why" in answer,
            "hasEvidenceBySource": "## Evidence By Source" in answer,
            "hasConflicts": "## Conflicts / Caveats" in answer,
            "hasRecommendedNextQuestion": "## Recommended Next Question" in answer,
            "conflicts": response.get("conflicts") or [],
        }
        checks = [
            response.get("answerType") == "conflict",
            payload["hasWhy"],
            payload["hasEvidenceBySource"],
            payload["hasConflicts"],
            payload["hasRecommendedNextQuestion"],
            len(payload["conflicts"]) > 0,
            "Global Approval Policy" in answer,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 52 notebook answer schema regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1
        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
