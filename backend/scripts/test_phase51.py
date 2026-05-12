from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase51.db"
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
        id="src-phase51",
        title="Access Approval Runbook",
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
            "notebookContext": {
                "documentType": "sop",
                "sourceBrief": "This runbook explains how to approve access requests and when to escalate privileged access.",
                "keyPoints": [
                    "Validate requester identity first.",
                    "Escalate privileged access requests to security.",
                ],
                "notes": [
                    {
                        "id": "note-step-1",
                        "kind": "procedure",
                        "title": "Initial validation",
                        "text": "Validate requester identity before any approval action.",
                        "roles": ["step", "summary"],
                        "provenance": {"sourceId": "src-phase51", "chunkIds": ["chunk-phase51-1"], "sectionKeys": ["sec-step-1"]},
                    },
                    {
                        "id": "note-risk-1",
                        "kind": "risk",
                        "title": "Privileged access exception",
                        "text": "Escalate privileged access requests to security before final approval.",
                        "roles": ["exception", "risk"],
                        "provenance": {"sourceId": "src-phase51", "chunkIds": ["chunk-phase51-2"], "sectionKeys": ["sec-risk-1"]},
                    },
                ],
                "recommendedPrompts": [
                    "What steps should I follow first?",
                    "What exceptions or risks appear in this runbook?",
                ],
            },
        },
        checksum="phase51",
        trust_level="high",
        file_size=None,
        description="Notebook context regression source",
        tags=["sop", "access"],
        collection_id=None,
    )
    db.add_all(
        [
            source,
            SourceChunk(
                id="chunk-phase51-1",
                source_id=source.id,
                chunk_index=0,
                section_title="Step 1",
                page_number=1,
                content="Validate requester identity before any approval action.",
                token_count=8,
                embedding_id=None,
                metadata_json={"sectionRole": "step", "parentSectionKey": "sec-step-1"},
                span_start=0,
                span_end=55,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-phase51-2",
                source_id=source.id,
                chunk_index=1,
                section_title="Security Exception",
                page_number=1,
                content="Escalate privileged access requests to security before final approval.",
                token_count=10,
                embedding_id=None,
                metadata_json={"sectionRole": "exception", "parentSectionKey": "sec-risk-1"},
                span_start=56,
                span_end=127,
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
        response = ask(db, "Summarize the first step in the access approval runbook.", source_id="src-phase51")
        diagnostics = response.get("diagnostics") or {}
        top_candidates = diagnostics.get("topCandidates") or []
        selected_context = diagnostics.get("selectedContext") or []
        citations = response.get("citations") or []

        payload = {
            "success": True,
            "answerType": response.get("answerType"),
            "topCandidateTypes": [item.get("candidateType") for item in top_candidates[:5]],
            "selectedContextTypes": [item.get("candidateType") for item in selected_context[:5]],
            "citationTypes": [item.get("candidateType") for item in citations],
            "scope": response.get("scope"),
            "suggestedPromptCount": len(response.get("suggestedPrompts") or []),
        }

        checks = [
            "notebook_note" in payload["topCandidateTypes"],
            "notebook_note" in payload["selectedContextTypes"],
            any(candidate_type == "notebook_note" for candidate_type in payload["citationTypes"]),
            response.get("answerType") in {"summary", "step_by_step"},
            response.get("scope", {}).get("id") == "src-phase51",
            payload["suggestedPromptCount"] >= 2,
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 51 notebook note regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
