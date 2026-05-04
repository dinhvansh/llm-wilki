from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase14.db"
MIGRATION_DB_PATH = ROOT / "test_phase14_migration.db"
for path in [DB_PATH, MIGRATION_DB_PATH]:
    if path.exists():
        path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.core.health import readiness_payload  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import Job  # noqa: E402
from app.services.job_queue import enqueue_source_job  # noqa: E402
from app.services.jobs import cancel_job, create_job, get_job, retry_job  # noqa: E402
from app.services.sources import create_text_source_record, get_source_by_id  # noqa: E402
from app.worker import run_once  # noqa: E402


def run_migration_smoke() -> bool:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{MIGRATION_DB_PATH.as_posix()}"
    env["JOB_QUEUE_BACKEND"] = "database"
    env["DEBUG"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", "from alembic.config import main; main()", "-c", "alembic.ini", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return False
    return MIGRATION_DB_PATH.exists()


def main() -> int:
    migration_ok = run_migration_smoke()
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        source, _ = create_text_source_record(
            db,
            title="Phase 14 Worker Source",
            content="Phase 14 worker source validates durable database queue processing and migration-backed startup.",
            actor="Phase14 Test",
        )
        job = enqueue_source_job(db, job_type="ingest", source_id=source.id, actor="Phase14 Test", logs=["Queued by Phase 14 test"])
        queued_job = get_job(db, job.id)
        processed = run_once()
        db.expire_all()
        processed_job = get_job(db, job.id)
        processed_source = get_source_by_id(db, source.id)

        pending = create_job(db, "rebuild", "src-001", status="pending", logs=["Pending cancel test"], actor="Phase14 Test")
        canceled = cancel_job(db, pending.id)

        failed = create_job(db, "rebuild", "src-001", status="failed", logs=["Failed retry test"], actor="Phase14 Test", attempt=1, max_attempts=2)
        retry = retry_job(db, failed.id, actor="Phase14 Retry")
        retry_payload = get_job(db, retry.id) if retry else None
        db.query(Job).filter(Job.id == failed.id).update({"attempt": 2})
        db.commit()
        retry_blocked = retry_job(db, failed.id, actor="Phase14 Retry")

        ready = readiness_payload()

        payload = {
            "success": True,
            "migrationOk": migration_ok,
            "queuedStatus": queued_job["status"] if queued_job else None,
            "processed": processed,
            "processedJobStatus": processed_job["status"] if processed_job else None,
            "processedSourceStatus": processed_source["parseStatus"] if processed_source else None,
            "canceledStatus": canceled["status"] if canceled else None,
            "retryAttempt": retry_payload["attempt"] if retry_payload else None,
            "retryOfJobId": retry_payload["retryOfJobId"] if retry_payload else None,
            "retryBlockedAtMaxAttempts": retry_blocked is None,
            "readinessOk": ready["ok"],
            "redisSkipped": bool(ready["checks"]["redis"].get("skipped")),
        }
        checks = [
            payload["migrationOk"],
            payload["queuedStatus"] == "pending",
            payload["processed"],
            payload["processedJobStatus"] == "completed",
            payload["processedSourceStatus"] == "indexed",
            payload["canceledStatus"] == "canceled",
            payload["retryAttempt"] == 2,
            payload["retryOfJobId"] == failed.id,
            payload["retryBlockedAtMaxAttempts"],
            payload["readinessOk"],
            payload["redisSkipped"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 14 production backbone checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
