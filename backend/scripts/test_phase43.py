from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase43.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from scripts.evaluate_quality import evaluate  # noqa: E402


def main() -> int:
    report = evaluate()
    averages = report.get("averages", {})
    quality_gates = report.get("qualityGates", {})

    payload = {
        "success": True,
        "retrievalRecallAt5": averages.get("retrievalRecallAt5"),
        "retrievalRecallAt10": averages.get("retrievalRecallAt10"),
        "rerankPrecisionAt5": averages.get("rerankPrecisionAt5"),
        "answerFaithfulness": averages.get("answerFaithfulness"),
        "qualityGates": quality_gates,
    }

    checks = [
        isinstance(averages.get("retrievalRecallAt5"), (int, float)),
        isinstance(averages.get("retrievalRecallAt10"), (int, float)),
        isinstance(averages.get("rerankPrecisionAt5"), (int, float)),
        isinstance(averages.get("answerFaithfulness"), (int, float)),
        quality_gates.get("retrievalRecallAt5") is True,
        quality_gates.get("retrievalRecallAt10") is True,
        quality_gates.get("rerankPrecisionAt5") is True,
        quality_gates.get("answerFaithfulness") is True,
    ]

    if not all(checks):
        payload["success"] = False
        payload["message"] = "Phase 43 retrieval/rerank/faithfulness eval metrics regression failed"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
