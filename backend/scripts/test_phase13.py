from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase13.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services import sources as source_service  # noqa: E402
from app.services.jobs import create_job, get_job, run_source_processing_job  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        text_source, _ = source_service.create_text_source_record(
            db,
            title="Connector Paste Demo",
            content=(
                "Connector Paste Demo: URL and pasted text sources should enter the same ingest pipeline. "
                "Phase 13 validates source metadata, suggestions, and generated pages."
            ),
            source_type="txt",
            collection_id="col-002",
            actor="Phase13 Test",
        )
        text_result = source_service.ingest_source(db, text_source.id)

        transcript_source, _ = source_service.create_text_source_record(
            db,
            title="Transcript Demo",
            content=(
                "Speaker A: In 2026, the team reviewed the RAG rollout timeline. "
                "Speaker B: The next milestone is a connector expansion review."
            ),
            source_type="transcript",
            actor="Phase13 Test",
        )
        transcript_result = source_service.ingest_source(db, transcript_source.id)

        original_fetch = source_service.fetch_url_content
        source_service.fetch_url_content = lambda url: (
            "URL Connector Demo",
            b"URL Connector Demo: web content parser extracted title and readable text for ingest. The article mentions RAG connectors in 2026.",
            "text/html",
            {
                "inputConnector": "url",
                "sourceKind": "web",
                "fetchedUrl": url,
                "contentType": "text/html",
                "rawBytes": 128,
                "readableCharCount": 118,
                "validation": {"maxBytes": source_service.MAX_CONNECTOR_BYTES},
            },
        )
        try:
            url_source, _ = source_service.create_url_source_record(
                db,
                url="https://example.com/wiki-connectors",
                collection_id="col-002",
                actor="Phase13 Test",
            )
        finally:
            source_service.fetch_url_content = original_fetch
        url_result = source_service.ingest_source(db, url_source.id)

        image_source, _ = source_service.create_source_record(
            db,
            filename="scan-demo.png",
            mime_type="image/png",
            file_size=16,
            file_bytes=b"not-a-real-image",
            actor="Phase13 Test",
        )
        image_job = create_job(db, "ingest", image_source.id, status="pending", logs=["Image upload received"], actor="Phase13 Test")
        run_source_processing_job(image_job.id, image_source.id)
        db.expire_all()
        image_result = source_service.get_source_by_id(db, image_source.id)
        image_job_detail = get_job(db, image_job.id)

        validation_failed = False
        try:
            source_service.create_text_source_record(db, title="Too short", content="tiny", actor="Phase13 Test")
        except ValueError:
            validation_failed = True

        payload = {
            "success": True,
            "textStatus": text_result["parseStatus"] if text_result else None,
            "textConnector": text_result["metadataJson"].get("inputConnector") if text_result else None,
            "textCollectionId": text_result["collectionId"] if text_result else None,
            "transcriptType": transcript_result["sourceType"] if transcript_result else None,
            "urlStatus": url_result["parseStatus"] if url_result else None,
            "urlValue": url_result["url"] if url_result else None,
            "urlConnector": url_result["metadataJson"].get("inputConnector") if url_result else None,
            "imageStatus": image_result["parseStatus"] if image_result else None,
            "imageJobStatus": image_job_detail["status"] if image_job_detail else None,
            "imageJobHasError": bool(image_job_detail and image_job_detail["errorMessage"]),
            "validationFailed": validation_failed,
        }
        checks = [
            payload["textStatus"] == "indexed",
            payload["textConnector"] == "txt",
            payload["textCollectionId"] == "col-002",
            payload["transcriptType"] == "transcript",
            payload["urlStatus"] == "indexed",
            payload["urlValue"] == "https://example.com/wiki-connectors",
            payload["urlConnector"] == "url",
            payload["imageStatus"] == "failed",
            payload["imageJobStatus"] == "failed",
            payload["imageJobHasError"],
            payload["validationFailed"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 13 connector checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
