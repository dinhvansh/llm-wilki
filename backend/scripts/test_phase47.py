from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase47.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from scripts import compare_quality_runs, evaluate_quality  # noqa: E402


def main() -> int:
    evaluate_quality.evaluate(selected_tags=["followup"])
    evaluate_quality.evaluate(selected_tags=["conflict"])
    status = compare_quality_runs.main()
    report_path = ROOT / "evals" / "last_quality_compare.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    payload = {
        "success": True,
        "compareExitCode": status,
        "runType": report.get("runType"),
        "baselineTags": report.get("baseline", {}).get("tags"),
        "candidateTags": report.get("candidate", {}).get("tags"),
    }
    checks = [
        status == 0,
        payload["runType"] == "eval",
        "followup" in (payload["baselineTags"] or []) or "followup" in (payload["candidateTags"] or []),
        "conflict" in (payload["baselineTags"] or []) or "conflict" in (payload["candidateTags"] or []),
    ]
    if not all(checks):
        payload["success"] = False
        payload["message"] = "Phase 47 quality run comparison regression failed"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
