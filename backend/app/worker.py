from __future__ import annotations

import argparse
import time

from app.config import settings
from app.core.bootstrap import init_database
from app.db.database import SessionLocal
from app.services.jobs import claim_next_source_job, run_source_processing_job


def run_once() -> bool:
    db = SessionLocal()
    try:
        job = claim_next_source_job(db)
        if not job:
            return False
        job_id = job.id
        source_id = job.input_ref
    finally:
        db.close()

    run_source_processing_job(job_id, source_id)
    return True


def run_forever() -> None:
    while True:
        processed = run_once()
        if not processed:
            time.sleep(settings.JOB_WORKER_POLL_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Wiki source job worker")
    parser.add_argument("--once", action="store_true", help="Process at most one pending job then exit")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=settings.AUTO_SEED_DEMO_DATA)
    finally:
        db.close()

    if args.once:
        return 0 if run_once() else 2
    run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
