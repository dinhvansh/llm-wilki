from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase36.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_section_summary_source(db) -> None:
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-phase36-sop",
        title="Privileged Access SOP",
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
            "documentType": "sop",
            "authorityLevel": "official",
            "sourceStatus": "approved",
            "sectionSummaries": [
                {
                    "sectionKey": "sec-prerequisites",
                    "title": "Prerequisites",
                    "summary": "Requester identity and manager approval ticket must exist before privileged access approval.",
                    "roles": ["prerequisite"],
                    "headingPath": ["Prerequisites"],
                    "chunkCount": 1,
                },
                {
                    "sectionKey": "sec-step1",
                    "title": "Step 1",
                    "summary": "Validate requester identity in the access queue.",
                    "roles": ["step"],
                    "headingPath": ["Step 1"],
                    "chunkCount": 1,
                },
            ],
        },
        checksum="src-phase36-sop",
        trust_level="high",
        file_size=None,
        description="Procedure for privileged access approval.",
        tags=["sop", "access"],
        collection_id=None,
    )
    chunk = SourceChunk(
        id="chunk-phase36-sop",
        source_id=source.id,
        chunk_index=0,
        section_title="Step 1",
        page_number=1,
        content="Validate requester identity in the access queue before approval.",
        token_count=10,
        embedding_id=None,
        metadata_json={
            "sectionRole": "step",
            "parentSectionKey": "sec-step1",
            "parentSectionTitle": "Step 1",
            "parentSectionSummary": "Validate requester identity in the access queue.",
        },
        span_start=0,
        span_end=64,
        created_at=now,
    )
    db.add_all([source, chunk])
    db.commit()


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_section_summary_source(db)
        answer = ask(db, "What prerequisites are needed before privileged access approval?")
        diagnostics = answer.get("diagnostics") or {}
        top_candidates = diagnostics.get("topCandidates") or []
        selected_context = diagnostics.get("selectedContext") or []

        payload = {
            "success": True,
            "topCandidateTypes": [item.get("candidateType") for item in top_candidates[:5]],
            "selectedContextTypes": [item.get("candidateType") for item in selected_context[:5]],
            "hasSectionSummaryTopCandidate": any(item.get("candidateType") == "section_summary" for item in top_candidates),
            "hasSectionContext": any(item.get("candidateType") == "section_summary" for item in selected_context),
            "hasSectionKeyInContext": any(item.get("sectionKey") for item in selected_context if item.get("candidateType") == "section_summary"),
        }

        checks = [
            payload["hasSectionSummaryTopCandidate"] is True,
            payload["hasSectionContext"] is True,
            payload["hasSectionKeyInContext"] is True,
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 36 section summary retrieval regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
