from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase54.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "false"
sys.path.insert(0, str(ROOT))

from app.core.ingest import ensure_upload_dir, public_upload_url  # noqa: E402
from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Source  # noqa: E402
from app.services.sources import _build_multimodal_artifact_manifest, _persist_source_artifacts, get_source_artifacts  # noqa: E402


PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360606060000000050001A5F645400000000049454E44AE426082"
)


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uploads = ensure_upload_dir()
    source_path = uploads / "phase54-image.png"
    source_path.write_bytes(PNG_BYTES)
    try:
        now = datetime.now(timezone.utc)
        source = Source(
            id="src-phase54",
            title="UI Approval Screenshot",
            source_type="image_ocr",
            mime_type="image/png",
            file_path=str(source_path),
            url=None,
            uploaded_at=now,
            updated_at=now,
            created_by="tester",
            parse_status="completed",
            ingest_status="completed",
            metadata_json={
                "summary": "Screenshot showing approval banner and warning state.",
                "orderedBlocks": [
                    {
                        "type": "paragraph",
                        "content": "The screenshot highlights the approval banner above the warning summary.",
                    },
                    {
                        "type": "image",
                        "url": public_upload_url(source_path),
                        "alt": "Approval banner screenshot",
                    },
                ],
            },
            checksum="phase54",
            trust_level="high",
            description="Artifact persistence regression fixture",
            tags=["image", "artifact"],
            collection_id=None,
        )
        db.add(source)
        db.commit()

        manifest = _build_multimodal_artifact_manifest(source, source.metadata_json or {}, source_path)
        _persist_source_artifacts(db, source, manifest)
        db.commit()
        artifacts = get_source_artifacts(db, source.id)

        image_artifacts = [item for item in artifacts if item.get("artifactType") == "image"]
        original_image = next((item for item in artifacts if item.get("id") == "src-phase54-original-image"), None)
        payload = {
            "success": True,
            "artifactCount": len(artifacts),
            "imageArtifactCount": len(image_artifacts),
            "captionSources": [str(item.get("metadataJson", {}).get("captionSource")) for item in image_artifacts],
            "hasOriginalImage": original_image is not None,
            "originalImageSummary": original_image.get("summary") if original_image else None,
        }
        checks = [
            len(artifacts) >= 2,
            len(image_artifacts) >= 1,
            any(source in {"vision_model", "contextual_fallback"} for source in payload["captionSources"]),
            bool(payload["originalImageSummary"]),
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 54 image artifact persistence regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1
        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        db.close()
        if source_path.exists():
            source_path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
