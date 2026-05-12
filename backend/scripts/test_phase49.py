from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase49.db"
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
    source_policy = Source(
        id="src-phase49-policy",
        title="Deployment Approval Policy",
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
        checksum="phase49-policy",
        trust_level="high",
        file_size=None,
        description="Official deployment policy",
        tags=["policy"],
        collection_id=None,
    )
    source_note = Source(
        id="src-phase49-note",
        title="Deployment Meeting Note",
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
        checksum="phase49-note",
        trust_level="medium",
        file_size=None,
        description="Meeting note with weaker advice",
        tags=["note"],
        collection_id=None,
    )
    source_empty = Source(
        id="src-phase49-empty",
        title="Archive Label Guide",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "reference", "sourceStatus": "approved", "documentType": "reference"},
        checksum="phase49-empty",
        trust_level="medium",
        file_size=None,
        description="Reference document without deployment guidance",
        tags=["reference"],
        collection_id=None,
    )
    db.add_all(
        [
            source_policy,
            source_note,
            source_empty,
            SourceChunk(
                id="chunk-phase49-policy",
                source_id="src-phase49-policy",
                chunk_index=0,
                section_title="Approval Rule",
                page_number=1,
                content="Production deployment requires CAB approval before release.",
                token_count=8,
                embedding_id=None,
                metadata_json={"sectionRole": "rule"},
                span_start=0,
                span_end=58,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-phase49-note",
                source_id="src-phase49-note",
                chunk_index=0,
                section_title="Draft Advice",
                page_number=1,
                content="Meeting note says CAB approval can be skipped for small patches.",
                token_count=11,
                embedding_id=None,
                metadata_json={"sectionRole": "rule"},
                span_start=0,
                span_end=64,
                created_at=now,
            ),
            SourceChunk(
                id="chunk-phase49-empty",
                source_id="src-phase49-empty",
                chunk_index=0,
                section_title="Reference",
                page_number=1,
                content="Archive labels must follow fiscal-year naming conventions.",
                token_count=8,
                embedding_id=None,
                metadata_json={"sectionRole": "reference"},
                span_start=0,
                span_end=56,
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

        policy_answer = ask(db, "What approval is required before deployment?", source_id="src-phase49-policy")
        conflict_answer = ask(db, "What conflict exists between Deployment Approval Policy and Deployment Meeting Note?")
        empty_scope_answer = ask(db, "What approval is required before deployment?", source_id="src-phase49-empty")

        policy_prompts = policy_answer.get("suggestedPrompts") or []
        conflict_prompts = conflict_answer.get("suggestedPrompts") or []
        empty_prompts = empty_scope_answer.get("suggestedPrompts") or []

        payload = {
            "success": True,
            "policyPromptCategories": [item.get("category") for item in policy_prompts],
            "policyPromptTexts": [item.get("text") for item in policy_prompts],
            "conflictPromptCategories": [item.get("category") for item in conflict_prompts],
            "emptyPromptCategories": [item.get("category") for item in empty_prompts],
            "emptyPromptTexts": [item.get("text") for item in empty_prompts],
        }

        checks = [
            "policy" in payload["policyPromptCategories"] or "authority" in payload["policyPromptCategories"],
            any("Deployment Approval Policy" in text for text in payload["policyPromptTexts"]),
            "authority" in payload["conflictPromptCategories"] or "comparison" in payload["conflictPromptCategories"],
            "summary" in payload["emptyPromptCategories"],
            "clarify" in payload["emptyPromptCategories"] or "source_lookup" in payload["emptyPromptCategories"],
            any("Which source should I open first" in text for text in payload["emptyPromptTexts"]),
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 49 suggested prompt regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
