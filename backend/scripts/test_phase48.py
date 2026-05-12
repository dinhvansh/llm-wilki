from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase48.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(ROOT))

from app.db.database import SessionLocal  # noqa: E402
from app.db.database import Base, engine  # noqa: E402
from app.models import Collection, Page, PageSourceLink, Source, SourceChunk  # noqa: E402
from app.services.query import ask  # noqa: E402


def _seed_scope_data(db) -> None:
    now = datetime.now(timezone.utc)
    collection_a = Collection(
        id="col-phase48-a",
        name="Release Operations",
        slug="release-operations",
        description="Scoped deployment guidance",
        color="blue",
        created_at=now,
        updated_at=now,
    )
    collection_b = Collection(
        id="col-phase48-b",
        name="Draft Notes",
        slug="draft-notes",
        description="Unapproved working notes",
        color="amber",
        created_at=now,
        updated_at=now,
    )
    source_a = Source(
        id="src-phase48-a",
        title="Release Approval Policy",
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
        checksum="phase48-a",
        trust_level="high",
        file_size=None,
        description="Official release approval policy",
        tags=["policy"],
        collection_id=collection_a.id,
    )
    source_b = Source(
        id="src-phase48-b",
        title="Draft Release Note",
        source_type="markdown",
        mime_type="text/markdown",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "informal", "sourceStatus": "draft", "documentType": "note"},
        checksum="phase48-b",
        trust_level="low",
        file_size=None,
        description="Draft note with conflicting advice",
        tags=["note"],
        collection_id=collection_b.id,
    )
    source_c = Source(
        id="src-phase48-c",
        title="Empty Scope Reference",
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
        checksum="phase48-c",
        trust_level="medium",
        file_size=None,
        description="Reference source that does not mention approvals",
        tags=["reference"],
        collection_id=collection_a.id,
    )
    chunk_a = SourceChunk(
        id="chunk-phase48-a",
        source_id=source_a.id,
        chunk_index=0,
        section_title="Approval Rule",
        page_number=1,
        content="Production deployment requires CAB approval and a smoke test before rollout.",
        token_count=11,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=76,
        created_at=now,
    )
    chunk_b = SourceChunk(
        id="chunk-phase48-b",
        source_id=source_b.id,
        chunk_index=0,
        section_title="Draft Advice",
        page_number=1,
        content="Draft note says teams can skip CAB approval for quick release fixes.",
        token_count=12,
        embedding_id=None,
        metadata_json={"sectionRole": "note"},
        span_start=0,
        span_end=69,
        created_at=now,
    )
    chunk_c = SourceChunk(
        id="chunk-phase48-c",
        source_id=source_c.id,
        chunk_index=0,
        section_title="Reference",
        page_number=1,
        content="This reference describes naming conventions and archive labels.",
        token_count=9,
        embedding_id=None,
        metadata_json={"sectionRole": "reference"},
        span_start=0,
        span_end=63,
        created_at=now,
    )
    page = Page(
        id="page-phase48-a",
        slug="release-approval-policy-page",
        title="Release Approval Policy Page",
        page_type="policy",
        status="published",
        summary="Summary of official release approval guidance.",
        content_md="CAB approval is required before production rollout.",
        content_html=None,
        current_version=1,
        last_composed_at=now,
        last_reviewed_at=now,
        published_at=now,
        owner="tester",
        tags=["policy"],
        parent_page_id=None,
        key_facts=["CAB approval required"],
        related_page_ids=[],
        related_entity_ids=[],
        collection_id=collection_a.id,
    )
    link = PageSourceLink(id="psl-phase48-a", page_id=page.id, source_id=source_a.id)
    db.add_all([collection_a, collection_b, source_a, source_b, source_c, chunk_a, chunk_b, chunk_c, page, link])
    db.commit()


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_scope_data(db)

        collection_answer = ask(db, "What approval is required before deployment?", collection_id="col-phase48-a")
        source_answer = ask(db, "What approval is required before deployment?", source_id="src-phase48-a")
        page_answer = ask(db, "What approval is required before deployment?", page_id="page-phase48-a")
        empty_scope_answer = ask(db, "What approval is required before deployment?", source_id="src-phase48-c")

        payload = {
            "success": True,
            "collectionScope": collection_answer.get("scope"),
            "sourceScope": source_answer.get("scope"),
            "pageScope": page_answer.get("scope"),
            "collectionCitationSourceIds": [item.get("sourceId") for item in collection_answer.get("citations", [])],
            "sourceCitationSourceIds": [item.get("sourceId") for item in source_answer.get("citations", [])],
            "pageCitationSourceIds": [item.get("sourceId") for item in page_answer.get("citations", [])],
            "pageRelatedPageIds": [item.get("id") for item in page_answer.get("relatedPages", [])],
            "emptyScopeMatched": (empty_scope_answer.get("scope") or {}).get("matchedInScope"),
            "emptyScopeUncertainty": empty_scope_answer.get("uncertainty"),
        }

        checks = [
            payload["collectionScope"] and payload["collectionScope"].get("type") == "collection",
            payload["sourceScope"] and payload["sourceScope"].get("type") == "source",
            payload["pageScope"] and payload["pageScope"].get("type") == "page",
            set(payload["collectionCitationSourceIds"]) == {"src-phase48-a"},
            set(payload["sourceCitationSourceIds"]) == {"src-phase48-a"},
            set(payload["pageCitationSourceIds"]) == {"src-phase48-a"},
            "page-phase48-a" in payload["pageRelatedPageIds"],
            payload["emptyScopeMatched"] is False,
            isinstance(payload["emptyScopeUncertainty"], str) and "current source scope" in payload["emptyScopeUncertainty"],
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 48 scoped Ask AI regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
