from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase45.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from scripts.evaluate_quality import evaluate  # noqa: E402


def main() -> int:
    report = evaluate(selected_tags=["followup"])
    payload = {
        "success": True,
        "requestedTags": report.get("requestedTags"),
        "caseCount": report.get("caseCount"),
        "behaviorCaseCount": report.get("behaviorCaseCount"),
        "behaviorCaseIds": [item.get("id") for item in report.get("behaviorCases", [])],
        "qualityGates": report.get("qualityGates"),
    }
    checks = [
        payload["requestedTags"] == ["followup"],
        payload["caseCount"] == 0,
        payload["behaviorCaseCount"] == 2,
        set(payload["behaviorCaseIds"]) == {"clarification-followup", "followup-resolution"},
        payload["qualityGates"].get("allPassed") is True,
    ]
    if not all(checks):
        payload["success"] = False
        payload["message"] = "Phase 45 eval tag subset regression failed"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
