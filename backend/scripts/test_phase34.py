from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.database import Base
from app.models import Source, SourceChunk
from app.services import sources as source_service


def main() -> int:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "credit-policy.txt"
        source_path.write_text(
            "\n".join(
                [
                    "Global Credit Policy",
                    "",
                    "Scope",
                    "This policy applies to all regional finance teams.",
                    "",
                    "Policy Rule",
                    "Finance must escalate any customer credit request above 100000 USD.",
                    "",
                    "Exception",
                    "Unless the CFO approves a temporary waiver in writing.",
                ]
            ),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc)
        source = Source(
            id="src-phase34",
            title="Global Credit Policy",
            source_type="txt",
            mime_type="text/plain",
            file_path=str(source_path),
            url=None,
            uploaded_at=now,
            updated_at=now,
            created_by="Phase34 Test",
            parse_status="uploaded",
            ingest_status="uploaded",
            metadata_json={"sourceStatus": "draft", "authorityLevel": "reference", "owner": "Risk Team"},
            checksum="phase34",
            trust_level="medium",
            file_size=source_path.stat().st_size,
            description="",
            tags=[],
            collection_id=None,
        )
        session.add(source)
        session.commit()

        original_embed = source_service.embedding_client.embed_texts
        try:
            source_service.embedding_client.embed_texts = lambda *args, **kwargs: None
            result = source_service.ingest_source(session, source.id)
        finally:
            source_service.embedding_client.embed_texts = original_embed

        if not result:
            raise AssertionError("Expected ingest_source to return a result")

        serialized = source_service.get_source_by_id(session, source.id)
        chunks = source_service.get_source_chunks(session, source.id, page=1, page_size=20)["data"]
        updated = source_service.update_source_metadata(
            session,
            source.id,
            actor="Phase34 Test",
            trust_level="high",
            document_type="policy",
            source_status="approved",
            authority_level="official",
            effective_date="2026-05-04",
            version="2026.05",
            owner="Finance Governance",
            tags=["policy", "credit"],
            description="Approved global credit policy.",
        )

        payload = {
            "success": True,
            "documentType": serialized.get("documentType"),
            "chunkRoles": sorted({str((chunk.get("metadataJson") or {}).get("sectionRole") or "") for chunk in chunks}),
            "defaultSourceStatus": serialized.get("sourceStatus"),
            "defaultAuthorityLevel": serialized.get("authorityLevel"),
            "updatedTrustLevel": updated.get("trustLevel") if updated else None,
            "updatedSourceStatus": updated.get("sourceStatus") if updated else None,
            "updatedAuthorityLevel": updated.get("authorityLevel") if updated else None,
            "updatedOwner": updated.get("owner") if updated else None,
            "updatedVersion": updated.get("version") if updated else None,
            "updatedTags": updated.get("tags") if updated else None,
        }

        checks = [
            payload["documentType"] == "policy",
            "scope" in payload["chunkRoles"] or "rule" in payload["chunkRoles"] or "exception" in payload["chunkRoles"],
            payload["defaultSourceStatus"] == "draft",
            payload["defaultAuthorityLevel"] == "reference",
            payload["updatedTrustLevel"] == "high",
            payload["updatedSourceStatus"] == "approved",
            payload["updatedAuthorityLevel"] == "official",
            payload["updatedOwner"] == "Finance Governance",
            payload["updatedVersion"] == "2026.05",
            payload["updatedTags"] == ["policy", "credit"],
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 34 metadata/classification regression checks failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0

    session.close()


if __name__ == "__main__":
    raise SystemExit(main())
