from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "evals" / "last_quality_compare.json"
REPORT_MD = ROOT / "evals" / "last_quality_compare.md"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'quality_eval.db').as_posix()}")
sys.path.insert(0, str(ROOT))

from app.db.database import SessionLocal  # noqa: E402
from app.models import EvalRun  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two persisted quality runs.")
    parser.add_argument("--run-type", choices=["eval", "benchmark"], default="eval")
    parser.add_argument("--baseline-id")
    parser.add_argument("--candidate-id")
    return parser.parse_args(argv)


def _load_runs(run_type: str, baseline_id: str | None, candidate_id: str | None) -> tuple[EvalRun, EvalRun]:
    db = SessionLocal()
    try:
        query = db.query(EvalRun).filter(EvalRun.run_type == run_type).order_by(EvalRun.created_at.desc())
        if baseline_id and candidate_id:
            candidate = db.query(EvalRun).filter(EvalRun.id == candidate_id).first()
            baseline = db.query(EvalRun).filter(EvalRun.id == baseline_id).first()
        else:
            recent = query.limit(2).all()
            if len(recent) < 2:
                raise ValueError(f"Need at least 2 `{run_type}` runs to compare.")
            candidate, baseline = recent[0], recent[1]
        if not candidate or not baseline:
            raise ValueError("Could not load baseline/candidate runs.")
        return baseline, candidate
    finally:
        db.close()


def _numeric_deltas(left: dict, right: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    keys = sorted(set(left) | set(right))
    for key in keys:
        left_value = left.get(key)
        right_value = right.get(key)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            result[key] = {
                "baseline": left_value,
                "candidate": right_value,
                "delta": round(right_value - left_value, 4),
            }
    return result


def write_reports(report: dict) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Quality Run Comparison",
        "",
        f"- Run type: {report['runType']}",
        f"- Baseline: {report['baseline']['id']} ({report['baseline']['createdAt']})",
        f"- Candidate: {report['candidate']['id']} ({report['candidate']['createdAt']})",
        "",
        "## Summary Deltas",
    ]
    for key, delta in report["summaryDeltas"].items():
        lines.append(f"- `{key}` baseline={delta['baseline']} candidate={delta['candidate']} delta={delta['delta']}")
    lines.extend(["", "## Gate Changes"])
    for item in report["gateChanges"]:
        lines.append(f"- `{item['name']}` baseline={item['baseline']} candidate={item['candidate']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    baseline, candidate = _load_runs(args.run_type, args.baseline_id, args.candidate_id)
    summary_deltas = _numeric_deltas(baseline.summary_json.get("averages", baseline.summary_json), candidate.summary_json.get("averages", candidate.summary_json))
    baseline_gates = baseline.quality_gates_json or {}
    candidate_gates = candidate.quality_gates_json or {}
    gate_changes = [
        {"name": key, "baseline": baseline_gates.get(key), "candidate": candidate_gates.get(key)}
        for key in sorted(set(baseline_gates) | set(candidate_gates))
        if baseline_gates.get(key) != candidate_gates.get(key)
    ]
    report = {
        "success": True,
        "runType": args.run_type,
        "baseline": {
            "id": baseline.id,
            "createdAt": baseline.created_at.isoformat() if baseline.created_at else None,
            "success": baseline.success,
            "tags": baseline.tags_json or [],
        },
        "candidate": {
            "id": candidate.id,
            "createdAt": candidate.created_at.isoformat() if candidate.created_at else None,
            "success": candidate.success,
            "tags": candidate.tags_json or [],
        },
        "summaryDeltas": summary_deltas,
        "gateChanges": gate_changes,
    }
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
