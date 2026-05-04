from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase17.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.ingest import json_like_to_dict, summarize_text  # noqa: E402
from app.core.reliability import REVIEW_REASON_TAXONOMY, calibrate_confidence  # noqa: E402


def main() -> int:
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_quality.py"],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=180,
    )
    report_path = ROOT / "evals" / "last_eval_report.json"
    md_path = ROOT / "evals" / "last_eval_report.md"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    invalid_json_guard = False
    try:
        json_like_to_dict("invalid")
    except ValueError:
        invalid_json_guard = True
    summary, facts = summarize_text("Fallback", "A reliable fallback summary sentence should be generated from local text. Another sentence should become a key fact for evaluation.")
    confidence = calibrate_confidence(0.8, citation_count=2, expected_citations=3, trusted_source_count=1)
    payload = {
        "success": True,
        "evalExitCode": result.returncode,
        "reportSuccess": report.get("success"),
        "reportExists": report_path.exists(),
        "markdownExists": md_path.exists(),
        "caseCount": report.get("caseCount"),
        "citationCoverage": report.get("averages", {}).get("citationCoverage"),
        "retrievalHitRate": report.get("averages", {}).get("retrievalHitRate"),
        "invalidJsonGuard": invalid_json_guard,
        "fallbackSummaryOk": bool(summary and facts),
        "taxonomyHasUnsupportedClaim": "unsupported_claim" in REVIEW_REASON_TAXONOMY,
        "calibratedConfidence": confidence.calibrated,
    }
    checks = [
        payload["evalExitCode"] == 0,
        payload["reportSuccess"] is True,
        payload["reportExists"],
        payload["markdownExists"],
        payload["caseCount"] >= 3,
        payload["citationCoverage"] >= 0.5,
        payload["retrievalHitRate"] >= 1.0,
        payload["invalidJsonGuard"],
        payload["fallbackSummaryOk"],
        payload["taxonomyHasUnsupportedClaim"],
        0 < payload["calibratedConfidence"] <= 1,
    ]
    if not all(checks):
        payload["success"] = False
        payload["stdout"] = result.stdout
        payload["stderr"] = result.stderr
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

