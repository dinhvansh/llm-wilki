from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase12.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.jobs import cancel_job, create_job, get_job, job_step, list_jobs_for_input, retry_job, update_job  # noqa: E402
from app.services.collections import assign_page_collection  # noqa: E402
from app.services.audit import list_audit_logs  # noqa: E402
from app.services.pages import get_page_audit_logs, publish_page, unpublish_page, update_page_content  # noqa: E402
from app.services.review import approve_review_item, create_issue_page_from_review_item  # noqa: E402
from app.services.sources import archive_source, list_sources, restore_source  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        source_id = "src-001"
        failed = create_job(db, "rebuild", source_id, status="failed", logs=["Rebuild requested", "Parser failed"], actor="Phase12 Test")
        update_job(
            db,
            failed.id,
            error_message="Synthetic failure",
            steps=[job_step("parse", "failed", 42, {"error": "Synthetic failure"})],
            progress_percent=42,
            finished=True,
        )
        retry = retry_job(db, failed.id, actor="Phase12 Retry")
        pending = create_job(db, "ingest", source_id, status="pending", logs=["Upload received"])
        canceled = cancel_job(db, pending.id)
        source_jobs = list_jobs_for_input(db, source_id)
        failed_detail = get_job(db, failed.id)
        update_page_content(db, "page-002", "# Integration Standards\n\nUpdated audit test content.", "Audit test edit", author="Phase12 Test")
        publish_page(db, "page-002")
        unpublish_page(db, "page-002")
        assign_page_collection(db, "page-002", "col-002")
        create_issue_page_from_review_item(db, "rev-001")
        approve_review_item(db, "rev-001", "Phase 12 audit approval")
        archived_source = archive_source(db, "src-001")
        default_source_ids = [item["id"] for item in list_sources(db, page_size=100)["data"]]
        archived_source_ids = [item["id"] for item in list_sources(db, status="archived", page_size=100)["data"]]
        restored_source = restore_source(db, "src-001")
        audit_logs = get_page_audit_logs(db, "page-002")
        all_audit_logs = list_audit_logs(db, limit=200)

        payload = {
            "success": True,
            "failedJobId": failed.id,
            "retryJobId": retry.id if retry else None,
            "canceledStatus": canceled["status"] if canceled else None,
            "sourceJobCount": len(source_jobs),
            "detailHasLogs": bool(failed_detail and failed_detail["logsJson"]),
            "detailHasSteps": bool(failed_detail and failed_detail["stepsJson"]),
            "detailProgress": failed_detail["progressPercent"] if failed_detail else None,
            "retryActor": retry.actor if retry else None,
            "auditActions": [item["action"] for item in audit_logs],
            "allAuditActions": [item["action"] for item in all_audit_logs],
            "archivedSourceHidden": "src-001" not in default_source_ids,
            "archivedSourceListed": "src-001" in archived_source_ids,
            "restoredArchivedFlag": restored_source["metadataJson"].get("archived") if restored_source else None,
        }
        checks = [
            retry is not None,
            retry.input_ref == source_id if retry else False,
            retry.status == "pending" if retry else False,
            canceled and canceled["status"] == "canceled",
            len(source_jobs) >= 3,
            payload["detailHasLogs"],
            payload["detailHasSteps"],
            payload["detailProgress"] == 42,
            payload["retryActor"] == "Phase12 Retry",
            {"update_content", "publish", "unpublish", "assign_page_collection"}.issubset(set(payload["auditActions"])),
            {"approve_review", "create_issue_page", "source_archived", "archive_source", "restore_source"}.issubset(set(payload["allAuditActions"])),
            archived_source is not None and archived_source["metadataJson"].get("archived") is True,
            payload["archivedSourceHidden"],
            payload["archivedSourceListed"],
            payload["restoredArchivedFlag"] is False,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 12 job flow checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
