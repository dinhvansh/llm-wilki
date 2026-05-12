from __future__ import annotations

from collections.abc import Callable


def assemble_context_pack(
    *,
    candidates: list[dict],
    interpreted: dict,
    limit: int,
    retrieval_policy: Callable[[str], dict],
    comparison_source_pairs: Callable[[list[dict]], list[dict]],
    conflict_builder: Callable[[list[dict], dict], list[dict]],
) -> tuple[list[dict], list[dict], dict]:
    """Select grounded context roles for Ask without formatting the final answer."""
    intent = interpreted["intent"]
    policy = retrieval_policy(intent)
    filters = interpreted.get("filters", {})
    selected: list[dict] = []
    context_pack: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()
    desired_roles = list(policy["desired_roles"])

    def candidate_role(candidate: dict) -> str:
        planned_role = str(candidate.get("plannerStepRole") or "").strip().lower()
        note_roles = [str(role).lower() for role in ((candidate.get("notebook_note") or {}).get("roles") or [])]
        artifact = candidate.get("artifact") or {}
        artifact_type = str(artifact.get("artifactType") or "").lower()
        if planned_role in {"summary", "definition", "step", "risk", "authority", "comparison", "conflict", "change", "evidence"}:
            return "exception" if planned_role == "risk" else planned_role
        if intent == "comparison":
            pairs = comparison_source_pairs(candidates)
            if pairs:
                if candidate["id"] == pairs[0]["id"]:
                    return "comparison_a"
                if len(pairs) > 1 and candidate["id"] == pairs[1]["id"]:
                    return "comparison_b"
        if candidate["type"] == "page_summary":
            return "summary"
        if candidate["type"] == "notebook_note":
            if any(role in {"exception", "risk"} for role in note_roles):
                return "exception"
            if any(role in {"step", "procedure"} for role in note_roles):
                return "step"
            if any(role in {"summary", "definition"} for role in note_roles):
                return "summary" if "summary" in note_roles else "definition"
            if any(role in {"evidence", "authority"} for role in note_roles):
                return "evidence"
            return "detail"
        if candidate["type"] == "user_note":
            text = str(candidate.get("text") or "").lower()
            if any(marker in text for marker in {"risk", "caveat", "warning", "exception"}):
                return "exception"
            if any(marker in text for marker in {"step", "procedure", "checklist"}):
                return "step"
            return "evidence"
        if candidate["type"] == "artifact_summary":
            if artifact_type in {"structure", "notebook"}:
                return "summary"
            if artifact_type in {"table", "ocr"}:
                return "evidence"
            if artifact_type == "image":
                return "detail"
            return "detail"
        if candidate["type"] == "knowledge_unit":
            unit_type = str((candidate.get("knowledge_unit") or {}).unit_type if candidate.get("knowledge_unit") else "").lower()
            if unit_type in {"definition"}:
                return "definition"
            if unit_type in {"rule", "threshold", "condition", "decision"}:
                return "evidence"
            if unit_type in {"procedure_step"}:
                return "step"
            if unit_type in {"exception", "warning"}:
                return "exception"
            return "detail"
        if candidate["type"] == "section_summary":
            roles = [str(role).lower() for role in ((candidate.get("section_summary") or {}).get("roles") or [])]
            if any(role in {"exception", "warning"} for role in roles):
                return "exception"
            if any(role in {"step", "prerequisite"} for role in roles):
                return "step"
            if any(role in {"definition", "field_reference"} for role in roles):
                return "definition"
            return "summary"
        if candidate["type"] == "claim":
            if intent in {"policy_rule", "threshold", "conflict_check", "authority_check", "definition", "fact_lookup", "source_lookup"}:
                return "evidence"
            return "detail"
        chunk = candidate.get("chunk")
        title = (chunk.section_title if chunk else "") if chunk else ""
        lowered = title.lower()
        if "exception" in lowered or "warning" in lowered:
            return "exception"
        if "step" in lowered or intent == "procedure":
            return "step"
        return "evidence"

    def add_context_candidate(candidate: dict, role: str) -> bool:
        key = (candidate["type"], candidate["id"])
        if key in seen_keys:
            return False
        seen_keys.add(key)
        selected.append(candidate)
        context_pack.append(
            {
                "role": role,
                "candidateType": candidate["type"],
                "candidateId": candidate["id"],
                "artifactId": (candidate.get("artifact") or {}).get("id"),
                "artifactType": (candidate.get("artifact") or {}).get("artifactType"),
                "sourceId": candidate["source"].id if candidate.get("source") else None,
                "pageId": candidate["page"].id if candidate.get("page") else None,
                "sectionKey": (candidate.get("section_summary") or {}).get("sectionKey") or getattr(candidate.get("note_anchor"), "section_key", None),
                "text": candidate["text"][:800],
            }
        )
        return True

    if intent in {"comparison", "change_review"}:
        pairs = comparison_source_pairs(candidates)
        for side_index, candidate in enumerate(pairs[:2], start=1):
            add_context_candidate(candidate, f"comparison_{'a' if side_index == 1 else 'b'}")
        coverage = {
            "has_comparison_a": any(item["role"] == "comparison_a" for item in context_pack),
            "has_comparison_b": any(item["role"] == "comparison_b" for item in context_pack),
            "selectedCount": len(context_pack),
        }
        for candidate in candidates:
            if not add_context_candidate(candidate, "summary"):
                continue
            coverage["selectedCount"] = len(context_pack)
            if len(selected) >= limit:
                break
        return selected, context_pack, coverage

    if intent == "conflict_check":
        conflicts = conflict_builder(candidates, interpreted)
        if conflicts:
            conflict_sources = [conflicts[0].get("preferredSourceId"), conflicts[0].get("competingSourceId")]
            for side_index, source_id in enumerate([item for item in conflict_sources if item], start=1):
                candidate = next((item for item in candidates if item.get("source") and item["source"].id == source_id), None)
                if candidate:
                    add_context_candidate(candidate, f"conflict_side_{'a' if side_index == 1 else 'b'}")

    if filters.get("source_id"):
        source_artifact = next((candidate for candidate in candidates if candidate["type"] == "artifact_summary"), None)
        if source_artifact is not None:
            add_context_candidate(source_artifact, candidate_role(source_artifact))

    for role in desired_roles:
        for candidate in candidates:
            key = (candidate["type"], candidate["id"])
            if key in seen_keys or candidate["type"] not in policy["preferred_types"]:
                continue
            resolved_role = candidate_role(candidate)
            if resolved_role != role:
                continue
            add_context_candidate(candidate, role)
            if len(selected) >= limit:
                coverage = {f"has_{name}": any(item["role"] == name for item in context_pack) for name in desired_roles}
                return selected, context_pack, coverage
            break

    for candidate in candidates:
        if not add_context_candidate(candidate, candidate_role(candidate)):
            continue
        if len(selected) >= limit:
            break

    coverage = {f"has_{name}": any(item["role"] == name for item in context_pack) for name in desired_roles}
    coverage["selectedCount"] = len(context_pack)
    return selected, context_pack, coverage
