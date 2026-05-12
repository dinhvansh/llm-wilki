from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.database import Base  # noqa: E402
from app.models import Source  # noqa: E402
from app.services import sources as source_service  # noqa: E402


def main() -> int:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = Path(tmp_dir) / "source-sections.txt"
            source_path.write_text(
                "\n".join(
                    [
                        "Access Request SOP",
                        "",
                        "Prerequisites",
                        "Requester account and manager ticket must exist.",
                        "",
                        "Step 1",
                        "Open the queue and validate requester identity.",
                        "",
                        "Exception",
                        "Escalate privileged requests to security.",
                    ]
                ),
                encoding="utf-8",
            )

            source = Source(
                id="src-phase40",
                title="Access Request SOP",
                source_type="txt",
                mime_type="text/plain",
                file_path=str(source_path),
                url=None,
                uploaded_at=source_service.datetime.now(source_service.timezone.utc),
                updated_at=source_service.datetime.now(source_service.timezone.utc),
                created_by="Phase40 Test",
                parse_status="uploaded",
                ingest_status="uploaded",
                metadata_json={},
                checksum="phase40",
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
                raise AssertionError("Expected ingest_source result")

            serialized = source_service.get_source_by_id(session, source.id)
            metadata = serialized.get("metadataJson") or {}
            source_sections = list(metadata.get("sourceSections") or [])

            payload = {
                "success": True,
                "sourceSectionCount": len(source_sections),
                "titles": [str(item.get("title") or "") for item in source_sections],
                "hasChunkIndexes": all(isinstance(item.get("chunkIndexes"), list) and len(item.get("chunkIndexes")) > 0 for item in source_sections),
                "hasRoles": any(any(str(role) != "general" for role in (item.get("roles") or [])) for item in source_sections),
            }

            checks = [
                payload["sourceSectionCount"] >= 3,
                any(title == "Step 1" for title in payload["titles"]),
                payload["hasChunkIndexes"] is True,
                payload["hasRoles"] is True,
            ]

            if not all(checks):
                payload["success"] = False
                payload["message"] = "Phase 40 source sections normalization regression failed"
                sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
                return 1

            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
