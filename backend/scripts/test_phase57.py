from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase57.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(ROOT))

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Collection, CollectionMembership, Source, SourceChunk, User  # noqa: E402
from app.services.auth import build_actor, hash_password  # noqa: E402
from app.services.query import ask  # noqa: E402
import app.services.query as query_service  # noqa: E402


def _seed(db) -> str:
    now = datetime.now(timezone.utc)
    allowed_collection = Collection(
        id="col-phase57-allowed",
        name="Allowed Collection",
        slug="allowed-collection",
        description="Collection visible to restricted reader",
        color="green",
        created_at=now,
        updated_at=now,
    )
    blocked_collection = Collection(
        id="col-phase57-blocked",
        name="Blocked Collection",
        slug="blocked-collection",
        description="Collection hidden from restricted reader",
        color="red",
        created_at=now,
        updated_at=now,
    )
    allowed_source = Source(
        id="src-phase57-allowed",
        title="Allowed Deployment Policy",
        source_type="txt",
        mime_type="text/plain",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "approved", "sourceStatus": "approved", "documentType": "policy"},
        checksum="phase57-allowed",
        trust_level="high",
        file_size=None,
        description="Allowed policy data",
        tags=["policy"],
        collection_id=allowed_collection.id,
    )
    blocked_source = Source(
        id="src-phase57-blocked",
        title="Blocked Deployment Policy",
        source_type="txt",
        mime_type="text/plain",
        file_path=None,
        url=None,
        uploaded_at=now,
        updated_at=now,
        created_by="tester",
        parse_status="completed",
        ingest_status="completed",
        metadata_json={"authorityLevel": "approved", "sourceStatus": "approved", "documentType": "policy"},
        checksum="phase57-blocked",
        trust_level="high",
        file_size=None,
        description="Blocked policy data",
        tags=["policy"],
        collection_id=blocked_collection.id,
    )
    allowed_chunk = SourceChunk(
        id="chunk-phase57-allowed",
        source_id=allowed_source.id,
        chunk_index=0,
        section_title="Deployment Rule",
        page_number=1,
        content="Production deployment requires CAB approval with documented evidence.",
        token_count=9,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=68,
        created_at=now,
    )
    blocked_chunk = SourceChunk(
        id="chunk-phase57-blocked",
        source_id=blocked_source.id,
        chunk_index=0,
        section_title="Restricted Rule",
        page_number=1,
        content="Restricted policy says CAB approval can be skipped for emergency fixes.",
        token_count=11,
        embedding_id=None,
        metadata_json={"sectionRole": "rule"},
        span_start=0,
        span_end=71,
        created_at=now,
    )
    user = User(
        id="user-phase57-reader",
        email="reader.phase57@local.test",
        name="Restricted Reader",
        role="reader",
        password_hash=hash_password("reader123"),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    membership = CollectionMembership(
        id="membership-phase57",
        collection_id=allowed_collection.id,
        user_id=user.id,
        role="viewer",
        created_at=now,
        updated_at=now,
    )
    db.add_all(
        [
            allowed_collection,
            blocked_collection,
            allowed_source,
            blocked_source,
            allowed_chunk,
            blocked_chunk,
            user,
            membership,
        ]
    )
    db.commit()
    return user.id


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user_id = _seed(db)
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        actor = build_actor(db, user)
        original_retrieve = query_service._retrieve_candidates

        def retrieve_without_actor_scope(db_session, runtime, interpreted, query_embedding, query_variants=None, actor=None):
            return original_retrieve(
                db_session,
                runtime,
                interpreted,
                query_embedding,
                query_variants=query_variants,
                actor=None,
            )

        with patch("app.services.query._retrieve_candidates", side_effect=retrieve_without_actor_scope):
            response = ask(db, "What approval is required before deployment?", actor=actor)

        citations = response.get("citations") or []
        citation_source_ids = [item.get("sourceId") for item in citations]
        diagnostics = response.get("diagnostics") or {}
        payload = {
            "success": True,
            "scopeMode": actor.collection_scope_mode,
            "accessibleCollections": list(actor.accessible_collection_ids),
            "citationSourceIds": citation_source_ids,
            "blockedCandidateCount": diagnostics.get("blockedCandidateCount"),
            "blockedRerankedCount": diagnostics.get("blockedRerankedCount"),
            "blockedSelectedCount": diagnostics.get("blockedSelectedCount"),
            "blockedCitationCount": diagnostics.get("blockedCitationCount"),
            "selectedContextSourceIds": [item.get("sourceId") for item in diagnostics.get("selectedContext", [])],
        }
        checks = [
            payload["scopeMode"] == "restricted",
            payload["accessibleCollections"] == ["col-phase57-allowed"],
            all(source_id != "src-phase57-blocked" for source_id in payload["citationSourceIds"]),
            all(source_id != "src-phase57-blocked" for source_id in payload["selectedContextSourceIds"]),
            isinstance(payload["blockedCandidateCount"], int) and payload["blockedCandidateCount"] >= 1,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 57 permission-aware retrieval regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
