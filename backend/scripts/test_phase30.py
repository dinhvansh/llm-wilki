from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingest import build_claims


CASE_POLICY = [
    {
        "section_title": "Policy Rules",
        "content": (
            "Employees must submit travel expense claims within 7 days of completing the trip. "
            "If receipts are missing, the manager must approve an exception before reimbursement. "
            "Citation accuracy must exceed 90 percent for grounded answers."
        ),
        "metadata": {"headingPath": ["Travel Policy", "Submission Rules"], "blockTypes": ["paragraph"]},
    },
    {
        "section_title": "Notes",
        "content": "The system may sometimes continue processing various requests depending on context.",
        "metadata": {"headingPath": ["Travel Policy", "Open Notes"], "blockTypes": ["paragraph"]},
    },
]

CASE_SOP = [
    {
        "section_title": "Procedure",
        "content": (
            "1. Open the reimbursement portal and create a new request. "
            "2. Attach receipts and verify project code. "
            "3. Submit the request to Finance for validation."
        ),
        "metadata": {"headingPath": ["SOP", "Procedure"], "blockTypes": ["list"]},
    }
]

CASE_REFERENCE = [
    {
        "section_title": "Glossary",
        "content": (
            "Cost Center: A financial tracking unit used to assign expenses to a team or department. "
            "Audit Trail: A record of who changed workflow data and when."
        ),
        "metadata": {"headingPath": ["Reference", "Glossary"], "blockTypes": ["paragraph"]},
    }
]

CASE_CONFLICT = [
    {
        "section_title": "Conflicts",
        "content": (
            "Finance approves reimbursements after two business days. "
            "Operations reports that reimbursement may take five business days during quarter close. "
            "This delay creates risk for employee satisfaction and escalations."
        ),
        "metadata": {"headingPath": ["Operations Review", "Conflicts"], "blockTypes": ["paragraph"]},
    }
]


def _summarize(claims: list[dict]) -> dict:
    return {
        "claimCount": len(claims),
        "types": sorted({claim["claim_type"] for claim in claims}),
        "lowConfidenceCount": sum(1 for claim in claims if claim.get("metadata_json", {}).get("isLowConfidence")),
    }


def main() -> None:
    policy_claims = build_claims(CASE_POLICY, {})
    sop_claims = build_claims(CASE_SOP, {})
    reference_claims = build_claims(CASE_REFERENCE, {})
    conflict_claims = build_claims(CASE_CONFLICT, {})

    assert policy_claims, "Expected policy claims"
    assert sop_claims, "Expected SOP claims"
    assert reference_claims, "Expected reference claims"
    assert conflict_claims, "Expected conflict claims"

    policy_types = {claim["claim_type"] for claim in policy_claims}
    sop_types = {claim["claim_type"] for claim in sop_claims}
    reference_types = {claim["claim_type"] for claim in reference_claims}
    conflict_types = {claim["claim_type"] for claim in conflict_claims}

    assert "requirement" in policy_types or "rule" in policy_types, policy_types
    assert "condition" in policy_types or "metric" in policy_types, policy_types
    assert "instruction" in sop_types or "process" in sop_types or "requirement" in sop_types, sop_types
    assert "definition" in reference_types or "fact" in reference_types, reference_types
    assert "risk" in conflict_types or "decision" in conflict_types or "fact" in conflict_types, conflict_types

    assert any(claim.get("evidence_span_start") is not None and claim.get("evidence_span_end") is not None for claim in policy_claims), policy_claims
    assert all(claim.get("metadata_json", {}).get("evidenceExcerpt") for claim in policy_claims + sop_claims + reference_claims + conflict_claims), "Expected evidence excerpts"
    assert any(claim.get("metadata_json", {}).get("isLowConfidence") for claim in policy_claims), policy_claims
    assert any(claim.get("extraction_method") in {"heuristic", "llm"} for claim in policy_claims + sop_claims + reference_claims + conflict_claims), "Expected extraction method"

    print(
        {
            "success": True,
            "policy": _summarize(policy_claims),
            "sop": _summarize(sop_claims),
            "reference": _summarize(reference_claims),
            "conflict": _summarize(conflict_claims),
        }
    )


if __name__ == "__main__":
    main()
