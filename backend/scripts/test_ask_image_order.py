from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_ask_image_order.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Source, SourceChunk  # noqa: E402
from app.services.query import _collect_related_images  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        source = Source(
            id="src-image-order",
            title="Image order source",
            source_type="docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_path=None,
            url=None,
            uploaded_at="2026-04-23T00:00:00+00:00",
            updated_at="2026-04-23T00:00:00+00:00",
            created_by="Test",
            parse_status="indexed",
            ingest_status="indexed",
            metadata_json={
                "images": ["/uploads/fallback-3.png", "/uploads/fallback-2.png", "/uploads/fallback-1.png"],
                "orderedBlocks": [
                    {"type": "paragraph", "content": "Intro"},
                    {"type": "image", "url": "/uploads/doc-1.png"},
                    {"type": "paragraph", "content": "Middle"},
                    {"type": "image", "url": "/uploads/doc-2.png"},
                    {"type": "image", "url": "/uploads/doc-3.png"},
                ],
            },
            checksum="image-order",
            trust_level="medium",
            file_size=None,
            description="",
            tags=[],
        )
        chunk_late = SourceChunk(
            id="chunk-image-late",
            source_id=source.id,
            chunk_index=3,
            section_title="Late",
            page_number=4,
            content="Late chunk",
            token_count=2,
            embedding_id=None,
            metadata_json={},
            span_start=0,
            span_end=10,
            created_at="2026-04-23T00:00:00+00:00",
        )
        chunk_early = SourceChunk(
            id="chunk-image-early",
            source_id=source.id,
            chunk_index=1,
            section_title="Early",
            page_number=2,
            content="Early chunk",
            token_count=2,
            embedding_id=None,
            metadata_json={},
            span_start=0,
            span_end=10,
            created_at="2026-04-23T00:00:00+00:00",
        )

        images = _collect_related_images(db, [(0.9, chunk_late, source), (0.8, chunk_early, source)], limit=3)
        payload = {"success": images == ["/uploads/doc-1.png", "/uploads/doc-2.png", "/uploads/doc-3.png"], "images": images}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["success"] else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
