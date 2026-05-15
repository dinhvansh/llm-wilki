from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.answer_verifier import verify_answer_support  # noqa: E402
from app.services.query import _build_query_variants  # noqa: E402
from app.services.retrieval_quality_gate import evaluate_retrieval_quality  # noqa: E402


def _candidate(text: str, score: float = 0.8) -> dict:
    return {
        "type": "chunk",
        "id": f"cand-{abs(hash(text)) % 100000}",
        "text": text,
        "excerpt": text[:200],
        "score": score,
        "diagnostics": {"finalScore": score},
    }


def main() -> int:
    failures: list[str] = []

    variants_vi = _build_query_variants("Chinh sach nghi phep nam 2026 la gi", "vi", cross_lingual_enabled=True)
    if len(variants_vi) < 2:
        failures.append("cross-lingual rewrite should produce at least 2 query variants for Vietnamese query")

    variants_no_rewrite = _build_query_variants("Chinh sach nghi phep", "vi", cross_lingual_enabled=False)
    if len(variants_no_rewrite) != 1:
        failures.append("cross-lingual rewrite disabled should keep only original query")

    no_data = verify_answer_support(
        question="What is policy year 2026",
        answer="No data",
        interpreted={"intent": "fact_lookup"},
        selected_candidates=[],
        citations=[],
    )
    if no_data.get("finalDecision") != "no_answer":
        failures.append("verifier should return no_answer when there are no selected candidates")

    selected = [
        _candidate("Annual leave policy: employees have 12 days. Effective 2025.", 0.82),
        _candidate("Policy scope: full-time employees only.", 0.77),
    ]
    supported = verify_answer_support(
        question="What is annual leave policy",
        answer="Employees have 12 days annual leave for full-time staff.",
        interpreted={"intent": "fact_lookup"},
        selected_candidates=selected,
        citations=[{"id": "c1"}, {"id": "c2"}],
    )
    if supported.get("finalDecision") not in {"answer", "partial_answer"}:
        failures.append("verifier should not return no_answer when evidence and citations exist")

    gate = evaluate_retrieval_quality(
        question="annual leave policy",
        interpreted={"intent": "fact_lookup"},
        reranked_candidates=selected,
        selected_candidates=selected,
        context_coverage={"selectedCount": 2},
        scope_summary=None,
    )
    if "passed" not in gate or "status" not in gate:
        failures.append("retrieval quality gate should return structured status")

    payload = {
        "success": not failures,
        "checks": {
            "queryVariantsVi": len(variants_vi),
            "queryVariantsNoRewrite": len(variants_no_rewrite),
            "noDataDecision": no_data.get("finalDecision"),
            "supportedDecision": supported.get("finalDecision"),
            "gateStatus": gate.get("status"),
        },
        "failures": failures,
    }
    sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
