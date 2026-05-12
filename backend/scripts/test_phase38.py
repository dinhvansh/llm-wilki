from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase38.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import KnowledgeUnit, Source  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_sources(db) -> None:
    now = datetime.now(timezone.utc)
    section_source = Source(
        id="src-phase38-section",
        title="Privileged Access Approval SOP",
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
                    "sectionKey": "sec-prereq",
                    "title": "Prerequisites",
                    "summary": "Requester identity and privileged access request ticket must exist before privileged access approval.",
                    "roles": ["prerequisite"],
                    "headingPath": ["Prerequisites"],
                    "chunkCount": 1,
                }
            ],
        },
        checksum="phase38-section",
        trust_level="high",
        file_size=None,
        description="Privileged access approval SOP",
        tags=["sop", "privileged_access"],
        collection_id=None,
    )
    ku_source = Source(
        id="src-phase38-ku",
        title="Deployment Policy",
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
        checksum="phase38-ku",
        trust_level="high",
        file_size=None,
        description="Deployment policy",
        tags=["policy"],
        collection_id=None,
    )
    unit = KnowledgeUnit(
        id="ku-phase38",
        source_id=ku_source.id,
        source_chunk_id=None,
        claim_id=None,
        unit_type="threshold",
        title="Deployment threshold",
        text="Changes affecting more than 5000 users require CAB approval.",
        status="draft",
        review_status="approved",
        canonical_status="verified",
        confidence_score=0.95,
        topic="Threshold",
        entity_ids=[],
        evidence_span_start=None,
        evidence_span_end=None,
        metadata_json={"documentType": "policy"},
        created_at=now,
        updated_at=now,
    )
    db.add_all([section_source, ku_source, unit])
    db.commit()


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_sources(db)
        section_answer = ask(db, "What prerequisites are needed before privileged access approval?")
        unit_answer = ask(db, "What threshold requires CAB approval?")

        section_citation_types = [item.get("candidateType") for item in section_answer.get("citations") or []]
        unit_citation_types = [item.get("candidateType") for item in unit_answer.get("citations") or []]

        payload = {
            "success": True,
            "sectionCitationTypes": section_citation_types,
            "unitCitationTypes": unit_citation_types,
            "sectionHasSectionTitle": any(item.get("sectionTitle") for item in section_answer.get("citations") or []),
            "unitHasUnitId": any(item.get("unitId") for item in unit_answer.get("citations") or []),
        }

        checks = [
            "section_summary" in section_citation_types,
            "knowledge_unit" in unit_citation_types,
            payload["sectionHasSectionTitle"] is True,
            payload["unitHasUnitId"] is True,
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 38 candidate-backed citation regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
