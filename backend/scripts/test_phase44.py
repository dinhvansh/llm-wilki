from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase44.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models import EvalRun  # noqa: E402
from scripts import benchmark_retrieval, evaluate_quality  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
    finally:
        db.close()

    eval_report = evaluate_quality.evaluate()
    benchmark_status = benchmark_retrieval.main()

    db = SessionLocal()
    try:
        runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).all()
        payload = {
            "success": True,
            "runCount": len(runs),
            "runTypes": [run.run_type for run in runs],
            "successFlags": [run.success for run in runs],
        }
        checks = [
            benchmark_status == 0,
            bool(eval_report.get("success")),
            len(runs) >= 2,
            "eval" in payload["runTypes"],
            "benchmark" in payload["runTypes"],
            all(isinstance(flag, bool) for flag in payload["successFlags"]),
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 44 eval run persistence regression failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
