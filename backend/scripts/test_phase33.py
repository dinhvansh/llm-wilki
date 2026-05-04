from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase33.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_authority_conflict(db) -> None:
    now = datetime.now(timezone.utc)
    source_a = Source(
        id="src-auth-approved",
        title="Approved Credit Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "official", "sourceStatus": "approved"},
        checksum="approved-credit-policy",
        trust_level="high",
        file_size=None,
        description=None,
        tags=["policy"],
        collection_id=None,
    )
    source_b = Source(
        id="src-auth-note",
        title="Meeting Note Credit Policy",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "informal", "sourceStatus": "draft"},
        checksum="meeting-note-credit-policy",
        trust_level="medium",
        file_size=None,
        description=None,
        tags=["meeting_note"],
        collection_id=None,
    )
    chunk_a = SourceChunk(
        id="chunk-auth-approved",
        source_id=source_a.id,
        chunk_index=0,
        section_title="Credit policy rule",
        page_number=1,
        content="Credit approval threshold is 100,000 USD and finance must escalate anything above that amount.",
        token_count=14,
        embedding_id=None,
        metadata_json={},
        span_start=0,
        span_end=95,
        created_at=now,
    )
    chunk_b = SourceChunk(
        id="chunk-auth-note",
        source_id=source_b.id,
        chunk_index=0,
        section_title="Credit policy note",
        page_number=1,
        content="Credit approval threshold is 90,000 USD according to a meeting note draft that has not been approved.",
        token_count=17,
        embedding_id=None,
        metadata_json={},
        span_start=0,
        span_end=102,
        created_at=now,
    )
    db.add_all([source_a, source_b, chunk_a, chunk_b])
    db.commit()


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        _seed_authority_conflict(db)

        first = ask(db, "What is RAG architecture?")
        followup = ask(db, "nó áp dụng khi nào?", first["sessionId"])
        clarification = ask(db, "trả lời sai rồi", first["sessionId"])
        policy = ask(db, "What standards are required for deploying an LLM?")
        conflict = ask(db, "What is the credit approval threshold policy?")

        payload = {
            "success": True,
            "firstIntent": first.get("interpretedQuery", {}).get("intent"),
            "followupStandalone": followup.get("interpretedQuery", {}).get("standaloneQuery"),
            "followupClarification": followup.get("interpretedQuery", {}).get("needsClarification"),
            "clarificationType": clarification.get("answerType"),
            "clarificationTriggered": clarification.get("diagnostics", {}).get("clarificationTriggered"),
            "policyCandidateCount": policy.get("diagnostics", {}).get("candidateCount"),
            "policyTopCandidateTypes": [item.get("candidateType") for item in policy.get("diagnostics", {}).get("topCandidates", [])[:5]],
            "policyHasStructuredAnswer": "## Direct Answer" in (policy.get("answer") or ""),
            "conflictCount": len(conflict.get("conflicts") or []),
            "preferredConflictSource": (conflict.get("conflicts") or [{}])[0].get("preferredSourceTitle"),
            "topConflictRerank": conflict.get("diagnostics", {}).get("topCandidates", [{}])[0].get("rerankScore"),
            "contextCoverageKeys": sorted((conflict.get("diagnostics", {}).get("contextCoverage") or {}).keys()),
        }

        checks = [
            payload["firstIntent"] in {"fact_lookup", "summary", "definition"},
            isinstance(payload["followupStandalone"], str) and len(payload["followupStandalone"]) > 10,
            payload["followupClarification"] is False,
            payload["clarificationType"] == "clarification",
            payload["clarificationTriggered"] is True,
            isinstance(payload["policyCandidateCount"], int) and payload["policyCandidateCount"] > 0,
            any(candidate_type in {"chunk", "claim", "page_summary"} for candidate_type in payload["policyTopCandidateTypes"]),
            payload["policyHasStructuredAnswer"],
            payload["conflictCount"] >= 1,
            payload["preferredConflictSource"] == "Approved Credit Policy",
            payload["topConflictRerank"] is not None,
            len(payload["contextCoverageKeys"]) > 0,
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 33 Ask AI regression checks failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
