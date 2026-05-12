from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase53.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(ROOT))

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed(db) -> None:
    now = datetime.now(timezone.utc)
    source = Source(
        id="src-phase53",
        title="Artifact Driven Release Review",
        source_type="txt",
        mime_type="text/plain",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={
            "documentType": "report",
            "authorityLevel": "approved",
            "sourceStatus": "approved",
            "multimodalArtifacts": [
                {
                    "id": "src-phase53-notebook",
                    "sourceId": "src-phase53",
                    "artifactType": "notebook",
                    "title": "Notebook Context",
                    "status": "available",
                    "summary": "Notebook summary highlights release caveats and reviewer prompts.",
                    "previewText": "Prompt: What evidence should the reviewer inspect first?",
                    "metadataJson": {
                        "recommendedPrompts": [
                            "What evidence should the reviewer inspect first?"
                        ]
                    },
                },
                {
                    "id": "src-phase53-structure",
                    "sourceId": "src-phase53",
                    "artifactType": "structure",
                    "title": "Document Structure Map",
                    "status": "available",
                    "summary": "Sections include rollout summary, exceptions, and approval checklist.",
                    "previewText": "rollout summary, exceptions, approval checklist",
                    "metadataJson": {
                        "sectionSummaries": [{"title": "Approval Checklist"}]
                    },
                },
            ],
        },
        checksum="phase53",
        trust_level="high",
        description="Artifact retrieval regression fixture",
        tags=["artifact", "review"],
        collection_id=None,
    )
    chunk = SourceChunk(
        id="chunk-phase53",
        source_id=source.id,
        chunk_index=0,
        section_title="Approval Checklist",
        page_number=1,
        content="Reviewers must inspect artifact evidence before approving the rollout.",
        token_count=10,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=70,
        created_at=now,
    )
    db.add_all([source, chunk])
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
        response = ask(db, "Summarize this source and tell me the most important evidence.", source_id="src-phase53")
        citations = response.get("citations") or []
        diagnostics = response.get("diagnostics") or {}
        payload = {
            "success": True,
            "citationTypes": [item.get("candidateType") for item in citations],
            "artifactTypes": [item.get("artifactType") for item in citations],
            "selectedContextTypes": [item.get("candidateType") for item in (diagnostics.get("selectedContext") or [])],
        }
        checks = [
            "artifact_summary" in payload["citationTypes"],
            "notebook" in payload["artifactTypes"],
            "artifact_summary" in payload["selectedContextTypes"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 53 multimodal artifact citation regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1
        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
