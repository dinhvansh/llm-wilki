from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase50.db"
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
    source = Source(
        id="src-phase50",
        title="Power Toolkit Demo Runbook",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved", "documentType": "sop"},
        checksum="phase50",
        trust_level="high",
        file_size=None,
        description="Demo preparation and risk guidance",
        tags=["sop", "demo"],
        collection_id=None,
    )
    chunks = [
        SourceChunk(
            id="chunk-phase50-prep",
            source_id=source.id,
            chunk_index=0,
            section_title="Preparation",
            page_number=1,
            content="Before the Power Toolkit demo, prepare a sample environment, verify credentials, and preload the dataset.",
            token_count=14,
            embedding_id=None,
            metadata_json={"sectionRole": "step"},
            span_start=0,
            span_end=106,
            created_at=now,
        ),
        SourceChunk(
            id="chunk-phase50-risk",
            source_id=source.id,
            chunk_index=1,
            section_title="Risk Notes",
            page_number=1,
            content="The main demo risks are stale credentials, missing browser extensions, and inconsistent sample data.",
            token_count=14,
            embedding_id=None,
            metadata_json={"sectionRole": "exception"},
            span_start=107,
            span_end=208,
            created_at=now,
        ),
        SourceChunk(
            id="chunk-phase50-test",
            source_id=source.id,
            chunk_index=2,
            section_title="Test First",
            page_number=1,
            content="Test authentication, extension loading, and the first guided scenario before the live handoff.",
            token_count=13,
            embedding_id=None,
            metadata_json={"sectionRole": "step"},
            span_start=209,
            span_end=305,
            created_at=now,
        ),
    ]
    db.add(source)
    db.add_all(chunks)
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_data(db)
        response = ask(
            db,
            "If I want to demo Power Toolkit, what should I prepare first, what risks should I watch for, and what should I test first?",
            source_id="src-phase50",
        )
        interpreted = response.get("interpretedQuery") or {}
        planner = interpreted.get("planner") or {}
        diagnostics = response.get("diagnostics") or {}
        planning = diagnostics.get("planning") or {}
        context_roles = [item.get("role") for item in diagnostics.get("selectedContext") or []]
        subqueries = planner.get("subQueries") or []

        payload = {
            "success": True,
            "answerType": response.get("answerType"),
            "plannerStrategy": planner.get("strategy"),
            "subQueryCount": len(subqueries),
            "subQueryIntents": [item.get("intent") for item in subqueries],
            "contextRoles": context_roles,
            "planningStrategyInDiagnostics": planning.get("strategy"),
            "scope": response.get("scope"),
        }

        checks = [
            response.get("answerType") == "analysis",
            planner.get("strategy") == "decompose",
            len(subqueries) >= 3,
            "risk_review" in payload["subQueryIntents"],
            sum(1 for item in payload["subQueryIntents"] if item == "procedure") >= 2,
            "step" in context_roles,
            "exception" in context_roles,
            planning.get("strategy") == "decompose",
            response.get("scope", {}).get("id") == "src-phase50",
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 50 planner regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
