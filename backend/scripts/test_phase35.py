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
from app.models import Source
from app.services import sources as source_service


def main() -> int:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / "sop-policy.txt"
        source_path.write_text(
            "\n".join(
                [
                    "Access Approval Procedure",
                    "",
                    "Prerequisites",
                    "User account and manager request must already exist in the ticketing system.",
                    "",
                    "Step 1",
                    "Open the request queue and validate requester identity.",
                    "",
                    "Step 2",
                    "Approve the request if the user belongs to the allowed department.",
                    "",
                    "Exception",
                    "Escalate to security if the request includes privileged access.",
                ]
            ),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc)
        source = Source(
            id="src-phase35",
            title="Access Approval Procedure",
            source_type="txt",
            mime_type="text/plain",
            file_path=str(source_path),
            url=None,
            uploaded_at=now,
            updated_at=now,
            created_by="Phase35 Test",
            parse_status="uploaded",
            ingest_status="uploaded",
            metadata_json={},
            checksum="phase35",
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
            raise AssertionError("Expected ingest_source to return result")

        serialized = source_service.get_source_by_id(session, source.id)
        chunks = source_service.get_source_chunks(session, source.id, page=1, page_size=20)["data"]
        section_summaries = list((serialized.get("metadataJson") or {}).get("sectionSummaries") or [])
        chunk_profile = dict((serialized.get("metadataJson") or {}).get("chunkProfile") or {})

        roles = sorted({str((chunk.get("metadataJson") or {}).get("sectionRole") or "") for chunk in chunks})
        has_parent_summary = all(bool((chunk.get("metadataJson") or {}).get("parentSectionSummary")) for chunk in chunks)

        payload = {
            "success": True,
            "documentType": serialized.get("documentType"),
            "chunkCount": len(chunks),
            "sectionSummaryCount": len(section_summaries),
            "chunkProfileDocumentType": chunk_profile.get("documentType"),
            "roles": roles,
            "hasParentSummary": has_parent_summary,
            "sectionTitles": [str(item.get("title") or "") for item in section_summaries],
        }

        checks = [
            payload["documentType"] in {"sop", "policy"},
            payload["chunkCount"] >= 3,
            payload["sectionSummaryCount"] >= 3,
            payload["chunkProfileDocumentType"] == payload["documentType"],
            any(role in {"prerequisite", "step", "exception"} for role in roles),
            payload["hasParentSummary"] is True,
            any("Step 1" in title or "Step 2" in title for title in payload["sectionTitles"]),
        ]

        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 35 semantic chunking and section summary regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1

        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0

    session.close()


if __name__ == "__main__":
    raise SystemExit(main())
