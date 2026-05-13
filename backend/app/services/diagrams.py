from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.ingest import json_like_to_dict
from app.core.llm_client import llm_client
from app.core.runtime_config import load_runtime_snapshot
from app.models import Claim, Diagram, DiagramVersion, Page, PageSourceLink, Source, SourceChunk
from app.services.audit import create_audit_log, list_audit_logs


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts)[:80] or f"diagram-{uuid4().hex[:6]}"


def _unique_slug(db: Session, base_slug: str, diagram_id: str | None = None) -> str:
    slug = base_slug
    counter = 2
    while True:
        query = db.query(Diagram).filter(Diagram.slug == slug)
        if diagram_id:
            query = query.filter(Diagram.id != diagram_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _diagram_page_summaries(db: Session, page_ids: list[str]) -> list[dict]:
    if not page_ids:
        return []
    rows = db.query(Page).filter(Page.id.in_(page_ids)).all()
    by_id = {row.id: row for row in rows}
    return [
        {"id": page_id, "slug": by_id[page_id].slug, "title": by_id[page_id].title, "status": by_id[page_id].status}
        for page_id in page_ids
        if page_id in by_id
    ]


def _diagram_source_summaries(db: Session, source_ids: list[str]) -> list[dict]:
    if not source_ids:
        return []
    rows = db.query(Source).filter(Source.id.in_(source_ids)).all()
    by_id = {row.id: row for row in rows}
    return [
        {"id": source_id, "title": by_id[source_id].title, "sourceType": by_id[source_id].source_type, "parseStatus": by_id[source_id].parse_status}
        for source_id in source_ids
        if source_id in by_id
    ]


def _related_diagram_summaries(db: Session, diagram_ids: list[str]) -> list[dict]:
    if not diagram_ids:
        return []
    rows = db.query(Diagram).filter(Diagram.id.in_(diagram_ids)).all()
    by_id = {row.id: row for row in rows}
    return [
        {"id": diagram_id, "slug": by_id[diagram_id].slug, "title": by_id[diagram_id].title, "status": by_id[diagram_id].status}
        for diagram_id in diagram_ids
        if diagram_id in by_id
    ]


def serialize_diagram(record: Diagram, db: Session | None = None) -> dict:
    source_page_ids = record.source_page_ids or []
    source_ids = record.source_ids or []
    related_diagram_ids = record.related_diagram_ids or []
    flow_document = _ensure_flow_document(
        record.flow_document or {},
        record.spec_json or {},
        title=record.title,
        objective=record.objective or "",
        owner=record.owner,
        source_page_ids=source_page_ids,
        source_ids=source_ids,
    )
    return {
        "id": record.id,
        "slug": record.slug,
        "title": record.title,
        "objective": record.objective or "",
        "notation": record.notation,
        "status": record.status,
        "owner": record.owner,
        "collectionId": record.collection_id,
        "currentVersion": record.current_version,
        "flowDocument": flow_document,
        "sourcePageIds": source_page_ids,
        "sourceIds": source_ids,
        "actorLanes": record.actor_lanes or [],
        "entryPoints": record.entry_points or [],
        "exitPoints": record.exit_points or [],
        "relatedDiagramIds": related_diagram_ids,
        "relatedDiagrams": _related_diagram_summaries(db, related_diagram_ids) if db else [],
        "linkedPages": _diagram_page_summaries(db, source_page_ids) if db else [],
        "linkedSources": _diagram_source_summaries(db, source_ids) if db else [],
        "createdAt": _iso(record.created_at),
        "updatedAt": _iso(record.updated_at),
        "publishedAt": _iso(record.published_at),
    }


def serialize_diagram_version(record: DiagramVersion) -> dict:
    return {
        "id": record.id,
        "diagramId": record.diagram_id,
        "versionNo": record.version_no,
        "flowDocument": record.flow_document or flow_document_from_spec(record.spec_json or {}, title="", objective="", owner=""),
        "changeSummary": record.change_summary or "",
        "createdAt": _iso(record.created_at),
        "createdByAgentOrUser": record.created_by_agent_or_user,
    }


def _normalize_owner(label: str) -> str:
    value = re.sub(r"\s+", " ", (label or "").strip())
    return value[:80]


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index + 1}"


def _actor_id(label: str) -> str:
    base = slugify(label).replace("-", "_")
    return base or f"actor_{uuid4().hex[:6]}"


def _extract_step_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    numbered_re = re.compile(r"^\d+[\.\)]\s+")
    for raw_line in lines:
        line = numbered_re.sub("", raw_line).strip()
        if len(line) < 12:
            continue
        if raw_line[:1] in {"-", "*"} or numbered_re.match(raw_line):
            candidates.append(line[:220])
    if candidates:
        return candidates[:10]

    sentence_re = re.compile(r"(?<=[.!?])\s+")
    sentences = [part.strip() for part in sentence_re.split(text) if len(part.strip()) > 20]
    return sentences[:8]


def _extract_actor_candidates(text: str, owner: str | None = None) -> list[str]:
    actor_patterns = [
        re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:must|should|will|can|reviews?|approves?|submits?|creates?|publishes?|updates?|checks?|verifies?)\b"),
        re.compile(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\s*:\s"),
    ]
    actors: list[str] = []
    for pattern in actor_patterns:
        for match in pattern.finditer(text):
            candidate = _normalize_owner(match.group(1))
            if candidate and candidate not in actors:
                actors.append(candidate)
    if owner:
        normalized_owner = _normalize_owner(owner)
        if normalized_owner and normalized_owner not in actors:
            actors.insert(0, normalized_owner)
    if "System" not in actors:
        actors.append("System")
    return actors[:5]


def _pick_owner(step: str, actors: list[str], fallback_owner: str) -> str:
    lowered = step.lower()
    for actor in actors:
        if actor.lower() in lowered:
            return actor
    return fallback_owner or (actors[0] if actors else "System")


def _build_heuristic_generation(*, title: str, objective: str, text: str, owner: str | None, citations: list[dict]) -> dict:
    step_candidates = _extract_step_candidates(text)
    actors = _extract_actor_candidates(text, owner=owner)
    primary_owner = actors[0] if actors else "System"
    nodes: list[dict] = []
    edges: list[dict] = []
    main_flow: list[dict] = []
    decision_points: list[dict] = []
    exception_flow: list[dict] = []
    open_questions: list[str] = []

    start_label = objective.strip() or "Process starts"
    nodes.append({"id": "start", "type": "start", "label": start_label[:100], "owner": primary_owner})
    previous_node_id = "start"

    if not step_candidates:
        step_candidates = ["Review source material and define the first operational step."]
        open_questions.append("Tai lieu chua neu ro cac buoc xu ly chinh; can bo sung main flow.")

    for index, step in enumerate(step_candidates[:6]):
        owner_label = _pick_owner(step, actors, primary_owner)
        normalized_step = re.sub(r"\s+", " ", step).strip()[:160]
        is_decision = bool(re.search(r"\b(if|whether|approve|approved|reject|rejected|pass|fail)\b|\?", normalized_step, re.IGNORECASE))
        node_type = "decision" if is_decision else "task"
        node_id = _node_id("decision" if is_decision else "task", index)
        nodes.append({"id": node_id, "type": node_type, "label": normalized_step, "owner": owner_label})
        edges.append({"from": previous_node_id, "to": node_id})
        main_flow.append({"nodeId": node_id, "label": normalized_step, "owner": owner_label})
        if is_decision:
            approve_node_id = f"{node_id}-approve"
            reject_node_id = f"{node_id}-reject"
            nodes.append({"id": approve_node_id, "type": "task", "label": "Continue approved path", "owner": "System"})
            nodes.append({"id": reject_node_id, "type": "task", "label": "Return for exception handling", "owner": owner_label})
            edges.append({"from": node_id, "to": approve_node_id, "label": "Approve"})
            edges.append({"from": node_id, "to": reject_node_id, "label": "Reject"})
            decision_points.append({"nodeId": node_id, "label": normalized_step, "branches": ["Approve", "Reject"]})
            exception_flow.append({"nodeId": reject_node_id, "label": "Return for exception handling", "owner": owner_label})
            previous_node_id = approve_node_id
        else:
            previous_node_id = node_id

    end_node_id = "end"
    end_label = "Completed"
    if exception_flow:
        end_label = "Completed or returned for rework"
    nodes.append({"id": end_node_id, "type": "end", "label": end_label, "owner": "System"})
    edges.append({"from": previous_node_id, "to": end_node_id})

    if len(actors) <= 1:
        open_questions.append("Chua xac dinh ro actor/owner cho tung buoc; can reviewer xac nhan lanes.")
    if not decision_points:
        open_questions.append("Tai lieu chua the hien decision point ro rang; can xac nhan co reject/escalation path hay khong.")
    if not exception_flow:
        open_questions.append("Tai lieu chua mo ta exception path; can bo sung khi co retry/reject/escalation.")

    return {
        "scopeSummary": objective.strip() or f"BPM draft extracted from {title}.",
        "actors": [{"id": _actor_id(actor), "label": actor} for actor in actors],
        "nodes": nodes,
        "edges": edges,
        "mainFlow": main_flow,
        "decisionPoints": decision_points,
        "exceptionFlow": exception_flow,
        "openQuestions": open_questions[:5],
        "citations": citations[:12],
        "generation": {"mode": "heuristic"},
    }


def _build_llm_generation(*, title: str, objective: str, text: str, owner: str | None, citations: list[dict], source_kind: str) -> dict | None:
    runtime = load_runtime_snapshot()
    bpm_profile = runtime.profile_for_task("bpm_generation")
    if not llm_client.is_enabled(bpm_profile):
        return None

    system_prompt = (
        "You convert internal business documents into BPM draft JSON. "
        "Return strict JSON only. "
        "Do not invent actors, decisions, or exception paths when the document is ambiguous. "
        "Use openQuestions for missing or ambiguous business logic. "
        "Output keys: scopeSummary, actors, steps, decisions, exceptionFlow, openQuestions."
    )
    user_prompt = (
        f"Source kind: {source_kind}\n"
        f"Title: {title}\n"
        f"Objective: {objective}\n"
        f"Default owner: {owner or 'Unknown'}\n\n"
        "Document excerpt:\n"
        f"{text[:12000]}"
    )
    response = llm_client.complete(bpm_profile, system_prompt, user_prompt)
    if not response:
        return None

    try:
        payload = json_like_to_dict(response)
    except Exception:
        return None

    actor_labels = []
    for item in payload.get("actors", []):
        if isinstance(item, dict):
            label = _normalize_owner(str(item.get("label") or item.get("name") or ""))
        else:
            label = _normalize_owner(str(item))
        if label and label not in actor_labels:
            actor_labels.append(label)
    if owner and _normalize_owner(owner) not in actor_labels:
        actor_labels.insert(0, _normalize_owner(owner))
    if not actor_labels:
        actor_labels = _extract_actor_candidates(text, owner=owner)

    nodes: list[dict] = [{"id": "start", "type": "start", "label": (objective.strip() or "Process starts")[:100], "owner": actor_labels[0] if actor_labels else "System"}]
    edges: list[dict] = []
    main_flow: list[dict] = []
    previous_node_id = "start"

    steps = payload.get("steps", [])
    for index, item in enumerate(steps[:8]):
        if isinstance(item, dict):
            label = re.sub(r"\s+", " ", str(item.get("label") or item.get("step") or "")).strip()
            step_owner = _normalize_owner(str(item.get("owner") or "")) or _pick_owner(label, actor_labels, actor_labels[0] if actor_labels else "System")
        else:
            label = re.sub(r"\s+", " ", str(item)).strip()
            step_owner = _pick_owner(label, actor_labels, actor_labels[0] if actor_labels else "System")
        if not label:
            continue
        node_id = _node_id("task", index)
        nodes.append({"id": node_id, "type": "task", "label": label[:160], "owner": step_owner})
        edges.append({"from": previous_node_id, "to": node_id})
        main_flow.append({"nodeId": node_id, "label": label[:160], "owner": step_owner})
        previous_node_id = node_id

    decision_points: list[dict] = []
    exception_flow: list[dict] = []
    for index, item in enumerate(payload.get("decisions", [])[:3]):
        if isinstance(item, dict):
            label = re.sub(r"\s+", " ", str(item.get("label") or item.get("question") or "")).strip()
            branches = [str(branch).strip() for branch in item.get("branches", []) if str(branch).strip()]
            owner_label = _normalize_owner(str(item.get("owner") or "")) or (actor_labels[0] if actor_labels else "System")
        else:
            label = re.sub(r"\s+", " ", str(item)).strip()
            branches = ["Yes", "No"]
            owner_label = actor_labels[0] if actor_labels else "System"
        if not label:
            continue
        node_id = _node_id("decision", index)
        nodes.append({"id": node_id, "type": "decision", "label": label[:160], "owner": owner_label})
        edges.append({"from": previous_node_id, "to": node_id})
        decision_points.append({"nodeId": node_id, "label": label[:160], "branches": branches or ["Yes", "No"]})
        for branch_index, branch in enumerate((branches or ["Yes", "No"])[:2]):
            branch_node_id = f"{node_id}-branch-{branch_index + 1}"
            nodes.append({"id": branch_node_id, "type": "task", "label": f"{branch} path", "owner": owner_label})
            edges.append({"from": node_id, "to": branch_node_id, "label": branch})
            if branch_index == 1:
                exception_flow.append({"nodeId": branch_node_id, "label": f"{branch} path", "owner": owner_label})
        previous_node_id = f"{node_id}-branch-1"

    nodes.append({"id": "end", "type": "end", "label": "Completed", "owner": "System"})
    edges.append({"from": previous_node_id, "to": "end"})

    open_questions = [str(item).strip() for item in payload.get("openQuestions", []) if str(item).strip()]
    return {
        "scopeSummary": str(payload.get("scopeSummary") or objective or f"BPM draft extracted from {title}.").strip(),
        "actors": [{"id": _actor_id(actor), "label": actor} for actor in actor_labels[:5]],
        "nodes": nodes,
        "edges": edges,
        "mainFlow": main_flow,
        "decisionPoints": decision_points,
        "exceptionFlow": exception_flow,
        "openQuestions": open_questions[:6],
        "citations": citations[:12],
        "generation": {"mode": "llm", "provider": bpm_profile.provider, "model": bpm_profile.model},
    }


def _build_llm_flow_document(*, title: str, objective: str, text: str, owner: str | None, citations: list[dict], source_kind: str) -> dict | None:
    runtime = load_runtime_snapshot()
    bpm_profile = runtime.profile_for_task("bpm_generation")
    if not llm_client.is_enabled(bpm_profile):
        return None

    system_prompt = (
        "You generate OpenFlow document JSON for a process canvas. "
        "Return strict JSON only. "
        "Required top-level keys: version, engine, family, pages, metadata. "
        "Use engine='openflowkit', family='flowchart'. "
        "pages[0] must contain id, name, lanes, nodes, edges, groups, viewport. "
        "Each node must contain id, type, label, owner, position. "
        "Each edge must contain id, source, target, type, and optional label. "
        "Do not invent business logic. Put missing logic in metadata.openQuestions."
    )
    user_prompt = (
        f"Source kind: {source_kind}\n"
        f"Title: {title}\n"
        f"Objective: {objective}\n"
        f"Default owner: {owner or 'Unknown'}\n\n"
        f"Citations JSON: {citations[:8]}\n\n"
        "Document excerpt:\n"
        f"{text[:12000]}"
    )
    response = llm_client.complete(bpm_profile, system_prompt, user_prompt)
    if not response:
        return None
    try:
        payload = json_like_to_dict(response)
    except Exception:
        return None
    if not isinstance(payload, dict) or not payload.get("pages"):
        return None
    return _ensure_flow_document(payload, None, title=title, objective=objective, owner=(owner or "").strip(), source_page_ids=[], source_ids=[])


def _validate_generated_spec(spec_json: dict) -> dict:
    warnings: list[str] = []
    nodes = spec_json.get("nodes", [])
    edges = spec_json.get("edges", [])
    node_by_id = {str(node.get("id")): node for node in nodes if isinstance(node, dict) and node.get("id")}

    actor_labels = {str(actor.get("label")).strip() for actor in spec_json.get("actors", []) if isinstance(actor, dict) and str(actor.get("label")).strip()}
    decision_nodes = [node for node in nodes if isinstance(node, dict) and node.get("type") == "decision"]
    exception_flow = spec_json.get("exceptionFlow", [])

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("type") in {"task", "decision", "handoff", "subprocess"}:
            owner = str(node.get("owner") or "").strip()
            if not owner:
                warnings.append(f"Node `{node.get('id')}` is missing owner.")
            elif actor_labels and owner not in actor_labels and owner != "System":
                warnings.append(f"Node `{node.get('id')}` owner `{owner}` is not declared in actor lanes.")
        if node.get("type") == "decision":
            label = str(node.get("label") or "").strip()
            if "?" not in label and not re.search(r"\b(approve|reject|valid|eligible|complete|pass|fail|whether)\b", label, re.IGNORECASE):
                warnings.append(f"Decision `{node.get('id')}` label should read like a branching question or decision.")

    for decision in decision_nodes:
        branch_count = sum(1 for edge in edges if isinstance(edge, dict) and edge.get("from") == decision.get("id"))
        if branch_count < 2:
            warnings.append(f"Decision `{decision.get('id')}` should have at least two outgoing branches.")

    if not exception_flow:
        warnings.append("Diagram does not contain an explicit exception path.")

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("from") not in node_by_id or edge.get("to") not in node_by_id:
            warnings.append(f"Edge `{edge}` points to a missing node.")

    return {"isValid": len(warnings) == 0, "warnings": warnings}


def flow_document_from_spec(
    spec_json: dict,
    *,
    title: str,
    objective: str = "",
    owner: str = "",
    source_page_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> dict:
    actors = [actor for actor in spec_json.get("actors", []) if isinstance(actor, dict)]
    actor_labels = [str(actor.get("label") or actor.get("name") or "").strip() for actor in actors]
    actor_labels = [label for label in actor_labels if label]
    lanes = [
        {"id": _actor_id(label), "label": label, "x": 80 + index * 300, "width": 260}
        for index, label in enumerate(actor_labels or [owner or "System"])
    ]
    lane_by_label = {lane["label"]: lane for lane in lanes}
    spec_nodes = [node for node in spec_json.get("nodes", []) if isinstance(node, dict) and node.get("id")]
    nodes: list[dict] = []
    for index, node in enumerate(spec_nodes):
        node_owner = str(node.get("owner") or lanes[0]["label"]).strip()
        lane = lane_by_label.get(node_owner, lanes[0])
        node_type = str(node.get("type") or "task")
        nodes.append(
            {
                "id": str(node.get("id")),
                "type": node_type,
                "label": str(node.get("label") or "").strip() or node_type.title(),
                "owner": node_owner,
                "position": {"x": int(lane["x"]), "y": 90 + index * 120},
                "size": {"width": 220, "height": 72},
                "data": {
                    "citation": node.get("citation"),
                    "sourceRef": node.get("sourceRef"),
                },
            }
        )
    edges = []
    for index, edge in enumerate([item for item in spec_json.get("edges", []) if isinstance(item, dict)]):
        source = str(edge.get("from") or edge.get("source") or "").strip()
        target = str(edge.get("to") or edge.get("target") or "").strip()
        if not source or not target:
            continue
        edges.append(
            {
                "id": str(edge.get("id") or f"edge-{index + 1}"),
                "source": source,
                "target": target,
                "label": str(edge.get("label") or "").strip(),
                "type": str(edge.get("type") or "smoothstep"),
                "data": {
                    "citation": edge.get("citation"),
                    "sourceRef": edge.get("sourceRef"),
                },
            }
        )
    return {
        "version": "1.0",
        "engine": "openflowkit",
        "family": "flowchart",
        "pages": [
            {
                "id": "page-main",
                "name": "Main",
                "lanes": lanes,
                "nodes": nodes,
                "edges": edges,
                "groups": [],
                "viewport": {"x": 0, "y": 0, "zoom": 1},
            }
        ],
        "metadata": {
            "title": title,
            "objective": objective,
            "owner": owner,
            "sourceIds": source_ids or spec_json.get("sourceIds", []),
            "sourcePageIds": source_page_ids or spec_json.get("sourcePageIds", []),
            "reviewStatus": spec_json.get("reviewStatus") or "needs_review",
            "scopeSummary": spec_json.get("scopeSummary") or objective,
            "openQuestions": spec_json.get("openQuestions", []),
            "citations": spec_json.get("citations", []),
            "validation": spec_json.get("validation") or _validate_generated_spec(spec_json),
            "legacySpec": spec_json,
        },
    }


def spec_from_flow_document(flow_document: dict) -> dict:
    page = _first_flow_page(flow_document)
    nodes = []
    for node in page.get("nodes", []):
        if not isinstance(node, dict):
            continue
        nodes.append(
            {
                "id": node.get("id"),
                "type": node.get("type") or "task",
                "label": node.get("label") or "",
                "owner": node.get("owner") or "",
            }
        )
    edges = []
    for edge in page.get("edges", []):
        if not isinstance(edge, dict):
            continue
        edges.append(
            {
                "id": edge.get("id"),
                "from": edge.get("source"),
                "to": edge.get("target"),
                "label": edge.get("label") or "",
            }
        )
    metadata = flow_document.get("metadata") if isinstance(flow_document.get("metadata"), dict) else {}
    spec = dict(metadata.get("legacySpec") if isinstance(metadata.get("legacySpec"), dict) else {})
    spec.update(
        {
            "title": metadata.get("title") or "",
            "scopeSummary": metadata.get("scopeSummary") or metadata.get("objective") or "",
            "actors": [{"id": lane.get("id"), "label": lane.get("label")} for lane in page.get("lanes", []) if isinstance(lane, dict)],
            "nodes": nodes,
            "edges": edges,
            "openQuestions": metadata.get("openQuestions") or [],
            "citations": metadata.get("citations") or [],
            "reviewStatus": metadata.get("reviewStatus") or "needs_review",
        }
    )
    spec["validation"] = _validate_generated_spec(spec)
    return spec


def _first_flow_page(flow_document: dict | None) -> dict:
    if not isinstance(flow_document, dict):
        return {"id": "page-main", "name": "Main", "lanes": [], "nodes": [], "edges": [], "groups": [], "viewport": {}}
    pages = flow_document.get("pages")
    if isinstance(pages, list) and pages and isinstance(pages[0], dict):
        page = dict(pages[0])
    else:
        page = {"id": "page-main", "name": "Main"}
    page.setdefault("lanes", [])
    page.setdefault("nodes", [])
    page.setdefault("edges", [])
    page.setdefault("groups", [])
    page.setdefault("viewport", {})
    return page


def _ensure_flow_document(
    flow_document: dict | None,
    spec_json: dict | None,
    *,
    title: str,
    objective: str,
    owner: str,
    source_page_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> dict:
    if isinstance(flow_document, dict) and flow_document.get("pages"):
        metadata = flow_document.get("metadata") if isinstance(flow_document.get("metadata"), dict) else {}
        flow_document["metadata"] = {
            **metadata,
            "title": title,
            "objective": objective,
            "owner": owner,
            "sourcePageIds": source_page_ids or metadata.get("sourcePageIds") or [],
            "sourceIds": source_ids or metadata.get("sourceIds") or [],
        }
        return flow_document
    return flow_document_from_spec(
        spec_json or {},
        title=title,
        objective=objective,
        owner=owner,
        source_page_ids=source_page_ids or [],
        source_ids=source_ids or [],
    )


def _flow_lanes(flow_document: dict) -> list[str]:
    page = _first_flow_page(flow_document)
    return [str(lane.get("label")).strip() for lane in page.get("lanes", []) if isinstance(lane, dict) and str(lane.get("label")).strip()]


def _flow_entry_points(flow_document: dict) -> list[str]:
    page = _first_flow_page(flow_document)
    return [str(node.get("label")).strip() for node in page.get("nodes", []) if isinstance(node, dict) and node.get("type") == "start" and str(node.get("label")).strip()]


def _flow_exit_points(flow_document: dict) -> list[str]:
    page = _first_flow_page(flow_document)
    return [str(node.get("label")).strip() for node in page.get("nodes", []) if isinstance(node, dict) and node.get("type") == "end" and str(node.get("label")).strip()]


def validate_flow_document(flow_document: dict) -> dict:
    page = _first_flow_page(flow_document)
    warnings: list[str] = []
    nodes = [node for node in page.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in page.get("edges", []) if isinstance(edge, dict)]
    node_ids = {str(node.get("id")) for node in nodes if node.get("id")}
    lane_labels = {str(lane.get("label")).strip() for lane in page.get("lanes", []) if isinstance(lane, dict) and str(lane.get("label")).strip()}
    if not nodes:
        warnings.append("Flow has no nodes.")
    if not any(node.get("type") == "start" for node in nodes):
        warnings.append("Flow is missing a start node.")
    if not any(node.get("type") == "end" for node in nodes):
        warnings.append("Flow is missing an end node.")
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not str(node.get("label") or "").strip():
            warnings.append(f"Node `{node_id}` is missing label.")
        owner = str(node.get("owner") or "").strip()
        if node.get("type") in {"task", "decision", "handoff"} and not owner:
            warnings.append(f"Node `{node_id}` is missing owner.")
        if owner and lane_labels and owner not in lane_labels and owner != "System":
            warnings.append(f"Node `{node_id}` owner `{owner}` is not declared as a lane.")
        if node.get("type") == "decision":
            outgoing = [edge for edge in edges if edge.get("source") == node_id]
            if len(outgoing) < 2:
                warnings.append(f"Decision `{node_id}` should have at least two outgoing edges.")
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in node_ids or target not in node_ids:
            warnings.append(f"Edge `{edge.get('id')}` points to a missing node.")
    return {"isValid": len(warnings) == 0, "warnings": warnings}


def flow_document_to_mermaid(flow_document: dict) -> str:
    page = _first_flow_page(flow_document)
    lines = ["flowchart TD"]
    for node in [item for item in page.get("nodes", []) if isinstance(item, dict)]:
        node_id = re.sub(r"[^A-Za-z0-9_]", "_", str(node.get("id") or "node"))
        label = str(node.get("label") or node_id).replace('"', "'")
        node_type = str(node.get("type") or "task")
        if node_type == "decision":
            lines.append(f'  {node_id}{{"{label}"}}')
        elif node_type in {"start", "end"}:
            lines.append(f'  {node_id}(("{label}"))')
        else:
            lines.append(f'  {node_id}["{label}"]')
    for edge in [item for item in page.get("edges", []) if isinstance(item, dict)]:
        source = re.sub(r"[^A-Za-z0-9_]", "_", str(edge.get("source") or ""))
        target = re.sub(r"[^A-Za-z0-9_]", "_", str(edge.get("target") or ""))
        if not source or not target:
            continue
        label = str(edge.get("label") or "").replace('"', "'")
        connector = f' -- "{label}" --> ' if label else " --> "
        lines.append(f"  {source}{connector}{target}")
    return "\n".join(lines)


def flow_document_from_mermaid(source: str, *, title: str, objective: str = "", owner: str = "") -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    edge_re = re.compile(r"\s*--(?:\s*\"([^\"]*)\"\s*--)?\s*>\s*")
    node_re = re.compile(
        r"^\s*([A-Za-z0-9_-]+)\s*(?:\[\"?([^\]\"]+)\"?\]|\(\(\"?([^\)\"]+)\"?\)\)|\{\"?([^}\"]+)\"?\})"
    )

    def parse_endpoint(value: str) -> dict:
        endpoint = value.strip().rstrip(";")
        match = re.match(r"^([A-Za-z0-9_-]+)\s*(.*)$", endpoint)
        node_id = match.group(1) if match else endpoint
        shape = match.group(2) if match else ""
        label = node_id
        if "[\"" in shape or "[" in shape:
            label_match = re.search(r"\[\"?([^\]\"]+)\"?\]", shape)
            label = label_match.group(1) if label_match else node_id
            node_type = "task"
        elif "((" in shape:
            label_match = re.search(r"\(\(\"?([^\)\"]+)\"?\)\)", shape)
            label = label_match.group(1) if label_match else node_id
            node_type = "end"
        elif "{" in shape:
            label_match = re.search(r"\{\"?([^}\"]+)\"?\}", shape)
            label = label_match.group(1) if label_match else node_id
            node_type = "decision"
        else:
            node_type = "task"
        return {"id": node_id, "type": node_type, "label": label, "owner": owner or "System"}

    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("flowchart") or line.lower().startswith("graph"):
            continue
        edge_match = edge_re.search(line)
        if edge_match:
            source_node = parse_endpoint(line[: edge_match.start()])
            target_node = parse_endpoint(line[edge_match.end() :])
            if source_node["id"] not in nodes or nodes[source_node["id"]].get("type") == "task":
                nodes[source_node["id"]] = source_node
            if target_node["id"] not in nodes or nodes[target_node["id"]].get("type") == "task":
                nodes[target_node["id"]] = target_node
            edges.append({"id": f"edge-{len(edges) + 1}", "source": source_node["id"], "target": target_node["id"], "label": edge_match.group(1) or "", "type": "smoothstep"})
            continue
        node_match = node_re.match(line)
        if node_match:
            node_id = node_match.group(1)
            label = next((group for group in node_match.groups()[1:] if group), node_id)
            node_type = "decision" if "{" in line else "task"
            nodes[node_id] = {"id": node_id, "type": node_type, "label": label, "owner": owner or "System"}
    inbound = {str(edge.get("target")) for edge in edges}
    outbound = {str(edge.get("source")) for edge in edges}
    for node_id, node in nodes.items():
        if node["type"] == "task" and node_id not in inbound:
            node["type"] = "start"
        if node["type"] == "task" and node_id not in outbound:
            node["type"] = "end"
    ordered_nodes = []
    for index, node in enumerate(nodes.values()):
        ordered_nodes.append({**node, "position": {"x": 100 + (index % 3) * 260, "y": 120 + index * 110}, "size": {"width": 220, "height": 72}})
    spec = {
        "actors": [{"id": _actor_id(owner or "System"), "label": owner or "System"}],
        "nodes": [{"id": node["id"], "type": node["type"], "label": node["label"], "owner": node.get("owner")} for node in ordered_nodes],
        "edges": [{"from": edge["source"], "to": edge["target"], "label": edge.get("label", "")} for edge in edges],
        "reviewStatus": "needs_review",
    }
    document = flow_document_from_spec(spec, title=title, objective=objective, owner=owner or "System")
    document["pages"][0]["nodes"] = ordered_nodes
    document["pages"][0]["edges"] = edges
    document["metadata"]["validation"] = validate_flow_document(document)
    return document


def _ensure_traceability_fields(spec_json: dict) -> dict:
    nodes = [node for node in spec_json.get("nodes", []) if isinstance(node, dict) and node.get("id")]
    citations = [item for item in spec_json.get("citations", []) if isinstance(item, dict)]
    if citations and not spec_json.get("nodeCitations"):
        node_citations = []
        for index, node in enumerate(nodes):
            citation = citations[min(index, len(citations) - 1)]
            node_citations.append({"nodeId": node.get("id"), "citation": citation})
        spec_json["nodeCitations"] = node_citations
    if not spec_json.get("edgeCitations"):
        edge_citations = []
        for edge in [item for item in spec_json.get("edges", []) if isinstance(item, dict)]:
            matched = next((item for item in spec_json.get("nodeCitations", []) if item.get("nodeId") == edge.get("to")), None)
            if matched:
                edge_citations.append({"edgeKey": f"{edge.get('from')}->{edge.get('to')}", "citation": matched.get("citation")})
        spec_json["edgeCitations"] = edge_citations
    spec_json.setdefault("relatedFlows", [])
    spec_json.setdefault("subprocesses", [])
    spec_json.setdefault("handoffs", [])
    return spec_json


def _procedural_signal_score(text: str) -> tuple[float, list[str]]:
    lowered = text.lower()
    score = 0.0
    reasons: list[str] = []
    if re.search(r"^\s*(?:\d+[\.\)]|[-*])\s+", text, re.MULTILINE):
        score += 0.28
        reasons.append("Detected ordered steps or bullet workflow cues.")
    if re.search(r"\b(step|workflow|process|procedure|approval|handoff|escalation|submit|review|publish|reject|retry)\b", lowered):
        score += 0.32
        reasons.append("Detected procedural/business-process vocabulary.")
    if re.search(r"\b(if|when|otherwise|exception|fallback|approve|reject)\b", lowered):
        score += 0.18
        reasons.append("Detected branching or exception-path vocabulary.")
    if re.search(r"\b(owner|actor|team|reviewer|editor|system|operator)\b", lowered):
        score += 0.12
        reasons.append("Detected ownership or actor language.")
    return min(score, 0.9), reasons


def assess_page_bpm_fit(db: Session, page_id: str) -> dict | None:
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        return None
    text = "\n".join(
        [
            page.title or "",
            page.summary or "",
            page.content_md or "",
        ]
    )
    score, reasons = _procedural_signal_score(text)
    page_type = (page.page_type or "").lower()
    if page_type in {"sop", "issue"}:
        score = max(score, 0.86)
        reasons.insert(0, f"Page type `{page_type}` is strongly BPM-oriented.")
    elif page_type in {"overview", "source_derived", "timeline"}:
        score = max(score, 0.58)
        reasons.insert(0, f"Page type `{page_type}` may benefit from BPM when it describes operational flow.")
    elif page_type in {"glossary", "entity", "faq", "concept", "summary", "deep_dive"}:
        score = min(score, 0.44 if score < 0.45 else score)
        reasons.insert(0, f"Page type `{page_type}` is often reference-oriented, not always a process flow.")

    if score >= 0.7:
        classification = "recommended"
        recommended_action = "generate_bpm"
    elif score >= 0.45:
        classification = "optional"
        recommended_action = "review_manually"
    else:
        classification = "not_recommended"
        recommended_action = "keep_as_reference"

    return {
        "targetType": "page",
        "targetId": page.id,
        "title": page.title,
        "eligible": classification != "not_recommended",
        "score": round(score, 2),
        "classification": classification,
        "recommendedAction": recommended_action,
        "reasons": reasons[:5],
        "pageType": page.page_type,
    }


def assess_source_bpm_fit(db: Session, source_id: str) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    chunks = db.query(SourceChunk).filter(SourceChunk.source_id == source.id).order_by(SourceChunk.chunk_index.asc()).limit(8).all()
    text = "\n".join([source.title or "", source.description or "", *(chunk.content or "" for chunk in chunks)])
    score, reasons = _procedural_signal_score(text)
    tags = [str(tag).lower() for tag in (source.tags or [])]
    if any(tag in {"sop", "workflow", "operations", "runbook", "playbook"} for tag in tags):
        score = max(score, 0.84)
        reasons.insert(0, "Source tags indicate SOP/workflow content.")
    elif any(tag in {"glossary", "reference", "policy"} for tag in tags):
        score = min(score, 0.4 if score < 0.5 else score)
        reasons.insert(0, "Source tags suggest reference material rather than executable process flow.")

    source_type = (source.source_type or "").lower()
    if source_type in {"transcript"}:
        score = min(score + 0.05, 0.75)
        reasons.append("Transcript sources may contain operational handoffs that can be mapped into BPM.")

    if score >= 0.7:
        classification = "recommended"
        recommended_action = "generate_bpm"
    elif score >= 0.45:
        classification = "optional"
        recommended_action = "review_manually"
    else:
        classification = "not_recommended"
        recommended_action = "keep_as_reference"

    return {
        "targetType": "source",
        "targetId": source.id,
        "title": source.title,
        "eligible": classification != "not_recommended",
        "score": round(score, 2),
        "classification": classification,
        "recommendedAction": recommended_action,
        "reasons": reasons[:5],
        "sourceType": source.source_type,
        "tags": source.tags or [],
    }


def _source_citations_from_chunks(source: Source, chunks: list[SourceChunk], limit: int = 8) -> list[dict]:
    citations: list[dict] = []
    for chunk in chunks[:limit]:
        citations.append(
            {
                "sourceId": source.id,
                "sourceTitle": source.title,
                "chunkId": chunk.id,
                "chunkIndex": chunk.chunk_index,
                "chunkSectionTitle": chunk.section_title,
                "pageNumber": chunk.page_number,
                "snippet": (chunk.content or "")[:280],
                "sourceSpanStart": chunk.span_start,
                "sourceSpanEnd": chunk.span_end,
            }
        )
    return citations


def _page_citations(db: Session, page_id: str, limit: int = 8) -> list[dict]:
    rows = (
        db.query(Claim, SourceChunk, Source)
        .join(SourceChunk, SourceChunk.id == Claim.source_chunk_id)
        .join(Source, Source.id == SourceChunk.source_id)
        .join(PageSourceLink, PageSourceLink.source_id == Source.id)
        .filter(PageSourceLink.page_id == page_id)
        .order_by(Claim.extracted_at.desc())
        .limit(limit)
        .all()
    )
    citations: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for claim, chunk, source in rows:
        key = (source.id, chunk.id)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "sourceId": source.id,
                "sourceTitle": source.title,
                "claimId": claim.id,
                "claimText": claim.text,
                "chunkId": chunk.id,
                "chunkIndex": chunk.chunk_index,
                "chunkSectionTitle": chunk.section_title,
                "pageNumber": chunk.page_number,
                "snippet": (claim.text or chunk.content or "")[:280],
                "sourceSpanStart": chunk.span_start,
                "sourceSpanEnd": chunk.span_end,
            }
        )
    return citations


def _create_generated_diagram(
    db: Session,
    *,
    actor: str,
    title: str,
    objective: str,
    collection_id: str | None,
    source_page_ids: list[str],
    source_ids: list[str],
    owner: str | None,
    source_kind: str,
    text: str,
    citations: list[dict],
) -> dict:
    llm_flow_document = _build_llm_flow_document(
        title=title,
        objective=objective,
        text=text,
        owner=owner,
        citations=citations,
        source_kind=source_kind,
    )
    llm_spec = _build_llm_generation(
        title=title,
        objective=objective,
        text=text,
        owner=owner,
        citations=citations,
        source_kind=source_kind,
    )
    spec_json = llm_spec or _build_heuristic_generation(
        title=title,
        objective=objective,
        text=text,
        owner=owner,
        citations=citations,
    )
    spec_json["title"] = title
    spec_json["sourceKind"] = source_kind
    spec_json["sourcePageIds"] = source_page_ids
    spec_json["sourceIds"] = source_ids
    spec_json["reviewStatus"] = "needs_review"
    spec_json = _ensure_traceability_fields(spec_json)
    spec_json["validation"] = _validate_generated_spec(spec_json)
    actor_lanes = [actor_item.get("label") for actor_item in spec_json.get("actors", []) if isinstance(actor_item, dict) and actor_item.get("label")]
    entry_points = [str(node.get("label")).strip() for node in spec_json.get("nodes", []) if isinstance(node, dict) and node.get("type") == "start"]
    exit_points = [str(node.get("label")).strip() for node in spec_json.get("nodes", []) if isinstance(node, dict) and node.get("type") == "end"]
    flow_document = llm_flow_document or flow_document_from_spec(
        spec_json,
        title=title,
        objective=objective,
        owner=(owner or actor).strip() or actor,
        source_page_ids=source_page_ids,
        source_ids=source_ids,
    )
    flow_document["metadata"]["sourcePageIds"] = source_page_ids
    flow_document["metadata"]["sourceIds"] = source_ids
    flow_document["metadata"]["validation"] = validate_flow_document(flow_document)
    return create_diagram(
        db,
        title=title,
        objective=objective,
        owner=(owner or actor).strip() or actor,
        collection_id=collection_id,
        actor_lanes=[lane for lane in actor_lanes if lane],
        source_page_ids=source_page_ids,
        source_ids=source_ids,
        entry_points=[item for item in entry_points if item],
        exit_points=[item for item in exit_points if item],
        related_diagram_ids=[],
        spec_json=spec_json,
        flow_document=flow_document,
    )


def generate_diagram_from_page(db: Session, page_id: str, *, actor: str) -> dict | None:
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        return None
    source_ids = [source_id for (source_id,) in db.query(PageSourceLink.source_id).filter(PageSourceLink.page_id == page.id).all()]
    linked_sources = db.query(Source).filter(Source.id.in_(source_ids)).all() if source_ids else []
    linked_chunks = (
        db.query(SourceChunk)
        .filter(SourceChunk.source_id.in_(source_ids))
        .order_by(SourceChunk.source_id.asc(), SourceChunk.chunk_index.asc())
        .limit(12)
        .all()
        if source_ids
        else []
    )
    text_parts = [page.title, page.summary or "", page.content_md or ""]
    if linked_chunks:
        text_parts.append("\n\n".join(chunk.content for chunk in linked_chunks if chunk.content))
    text = "\n\n".join(part for part in text_parts if part)
    citations = _page_citations(db, page.id)
    if not citations and linked_sources:
        citations = _source_citations_from_chunks(linked_sources[0], linked_chunks)
    title = f"{page.title} BPM Flow"
    objective = page.summary or f"BPM draft generated from page `{page.title}`."
    return _create_generated_diagram(
        db,
        actor=actor,
        title=title,
        objective=objective,
        collection_id=page.collection_id,
        source_page_ids=[page.id],
        source_ids=source_ids,
        owner=page.owner,
        source_kind="page",
        text=text,
        citations=citations,
    )


def generate_diagram_from_source(db: Session, source_id: str, *, actor: str) -> dict | None:
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        return None
    chunks = db.query(SourceChunk).filter(SourceChunk.source_id == source.id).order_by(SourceChunk.chunk_index.asc()).limit(12).all()
    linked_page_ids = [page_id for (page_id,) in db.query(PageSourceLink.page_id).filter(PageSourceLink.source_id == source.id).all()]
    text_parts = [source.title, source.description or ""]
    text_parts.extend(chunk.content for chunk in chunks if chunk.content)
    text = "\n\n".join(part for part in text_parts if part)
    citations = _source_citations_from_chunks(source, chunks)
    objective = source.description or f"BPM draft generated from source `{source.title}`."
    return _create_generated_diagram(
        db,
        actor=actor,
        title=f"{source.title} BPM Flow",
        objective=objective,
        collection_id=source.collection_id,
        source_page_ids=linked_page_ids,
        source_ids=[source.id],
        owner=actor,
        source_kind="source",
        text=text,
        citations=citations,
    )


def list_diagrams(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    search: str | None = None,
    collection_id: str | None = None,
    page_id: str | None = None,
    source_id: str | None = None,
) -> dict:
    query = db.query(Diagram)
    if status:
        query = query.filter(Diagram.status == status)
    if collection_id == "standalone":
        query = query.filter(Diagram.collection_id.is_(None))
    elif collection_id:
        query = query.filter(Diagram.collection_id == collection_id)
    if page_id:
        query = query.filter(Diagram.source_page_ids.contains([page_id]))
    if source_id:
        query = query.filter(Diagram.source_ids.contains([source_id]))
    if search:
        needle = f"%{search.strip()}%"
        query = query.filter((Diagram.title.ilike(needle)) | (Diagram.objective.ilike(needle)))
    total = query.count()
    rows = (
        query.order_by(Diagram.updated_at.desc())
        .offset(max(0, page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "data": [serialize_diagram(row, db) for row in rows],
        "total": total,
        "page": page,
        "pageSize": page_size,
        "hasMore": page * page_size < total,
    }


def get_diagram_by_slug(db: Session, slug: str) -> dict | None:
    row = db.query(Diagram).filter(Diagram.slug == slug).first()
    return serialize_diagram(row, db) if row else None


def get_diagram_by_id(db: Session, diagram_id: str) -> Diagram | None:
    return db.query(Diagram).filter(Diagram.id == diagram_id).first()


def get_diagram_versions(db: Session, diagram_id: str) -> list[dict]:
    rows = (
        db.query(DiagramVersion)
        .filter(DiagramVersion.diagram_id == diagram_id)
        .order_by(DiagramVersion.version_no.desc())
        .all()
    )
    return [serialize_diagram_version(row) for row in rows]


def get_diagram_audit_logs(db: Session, diagram_id: str, limit: int = 50) -> list[dict]:
    return list_audit_logs(db, object_type="diagram", object_id=diagram_id, limit=limit)


def validate_diagram_flow(db: Session, diagram_id: str) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    flow_document = _ensure_flow_document(record.flow_document or {}, record.spec_json or {}, title=record.title, objective=record.objective or "", owner=record.owner, source_page_ids=record.source_page_ids or [], source_ids=record.source_ids or [])
    return validate_flow_document(flow_document)


def export_diagram_flow(db: Session, diagram_id: str, *, format: str = "json") -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    flow_document = _ensure_flow_document(record.flow_document or {}, record.spec_json or {}, title=record.title, objective=record.objective or "", owner=record.owner, source_page_ids=record.source_page_ids or [], source_ids=record.source_ids or [])
    normalized = format.strip().lower()
    if normalized == "mermaid":
        return {"format": "mermaid", "content": flow_document_to_mermaid(flow_document)}
    return {"format": "json", "content": flow_document}


def create_diagram_from_import(db: Session, *, title: str, objective: str, source: str, source_format: str, actor: str) -> dict:
    normalized = source_format.strip().lower()
    if normalized == "mermaid":
        flow_document = flow_document_from_mermaid(source, title=title, objective=objective, owner=actor)
    else:
        payload = json_like_to_dict(source)
        flow_document = _ensure_flow_document(payload, None, title=title, objective=objective, owner=actor)
    return create_diagram(
        db,
        title=title,
        objective=objective,
        owner=actor,
        actor_lanes=_flow_lanes(flow_document),
        entry_points=_flow_entry_points(flow_document),
        exit_points=_flow_exit_points(flow_document),
        flow_document=flow_document,
    )


def create_diagram(
    db: Session,
    *,
    title: str,
    owner: str,
    objective: str = "",
    collection_id: str | None = None,
    actor_lanes: list[str] | None = None,
    source_page_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    entry_points: list[str] | None = None,
    exit_points: list[str] | None = None,
    related_diagram_ids: list[str] | None = None,
    spec_json: dict | None = None,
    flow_document: dict | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    effective_flow_document = _ensure_flow_document(
        flow_document,
        spec_json or {},
        title=title.strip()[:255],
        objective=(objective or "").strip(),
        owner=owner,
        source_page_ids=source_page_ids or [],
        source_ids=source_ids or [],
    )
    effective_spec_json = spec_from_flow_document(effective_flow_document)
    record = Diagram(
        id=f"diag-{uuid4().hex[:8]}",
        slug=_unique_slug(db, slugify(title)),
        title=title.strip()[:255],
        objective=(objective or "").strip(),
        notation="bpm",
        status="draft",
        owner=owner,
        collection_id=collection_id,
        current_version=1,
        drawio_xml="",
        spec_json=effective_spec_json,
        flow_document=effective_flow_document,
        source_page_ids=source_page_ids or [],
        source_ids=source_ids or [],
        actor_lanes=actor_lanes or [],
        entry_points=entry_points or [],
        exit_points=exit_points or [],
        related_diagram_ids=related_diagram_ids or [],
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    db.add(
        DiagramVersion(
            id=f"diagver-{uuid4().hex[:8]}",
            diagram_id=record.id,
            version_no=1,
            drawio_xml="",
            spec_json=record.spec_json,
            flow_document=record.flow_document,
            change_summary="Initial diagram draft",
            created_at=now,
            created_by_agent_or_user=owner,
        )
    )
    create_audit_log(
        db,
        action="diagram_created",
        object_type="diagram",
        object_id=record.id,
        actor=owner,
        summary=f"Created diagram `{record.title}`",
        metadata={"diagramId": record.id, "diagramSlug": record.slug},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


@dataclass
class DiagramEditConflict(Exception):
    current_version: int


def update_diagram(
    db: Session,
    diagram_id: str,
    *,
    title: str,
    objective: str,
    owner: str,
    actor: str,
    collection_id: str | None,
    actor_lanes: list[str],
    source_page_ids: list[str],
    source_ids: list[str],
    entry_points: list[str],
    exit_points: list[str],
    related_diagram_ids: list[str],
    spec_json: dict | None = None,
    flow_document: dict | None = None,
    change_summary: str | None = None,
    expected_version: int | None = None,
) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    if expected_version is not None and expected_version != record.current_version:
        raise DiagramEditConflict(record.current_version)
    now = datetime.now(timezone.utc)
    record.title = title.strip()[:255]
    record.slug = _unique_slug(db, slugify(record.title), diagram_id=record.id)
    record.objective = (objective or "").strip()
    record.owner = owner.strip()[:128] or actor
    record.collection_id = collection_id
    record.actor_lanes = actor_lanes
    record.source_page_ids = source_page_ids
    record.source_ids = source_ids
    record.entry_points = entry_points
    record.exit_points = exit_points
    record.related_diagram_ids = related_diagram_ids
    effective_flow_document = _ensure_flow_document(
        flow_document,
        spec_json or {},
        title=record.title,
        objective=record.objective,
        owner=record.owner,
        source_page_ids=source_page_ids,
        source_ids=source_ids,
    )
    record.flow_document = effective_flow_document
    record.spec_json = spec_from_flow_document(effective_flow_document)
    record.drawio_xml = ""
    record.updated_at = now
    record.current_version += 1
    db.add(
        DiagramVersion(
            id=f"diagver-{uuid4().hex[:8]}",
            diagram_id=record.id,
            version_no=record.current_version,
            drawio_xml="",
            spec_json=record.spec_json,
            flow_document=record.flow_document,
            change_summary=(change_summary or "Updated diagram").strip()[:255],
            created_at=now,
            created_by_agent_or_user=actor,
        )
    )
    create_audit_log(
        db,
        action="diagram_updated",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Updated diagram `{record.title}`",
        metadata={"diagramId": record.id, "version": record.current_version},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


def publish_diagram(db: Session, diagram_id: str, *, actor: str, actor_metadata: dict | None = None) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    now = datetime.now(timezone.utc)
    record.status = "published"
    record.published_at = now
    record.updated_at = now
    create_audit_log(
        db,
        action="diagram_published",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Published diagram `{record.title}`",
        metadata={"diagramId": record.id, **(actor_metadata or {})},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


def unpublish_diagram(db: Session, diagram_id: str, *, actor: str, actor_metadata: dict | None = None) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    now = datetime.now(timezone.utc)
    record.status = "draft"
    record.updated_at = now
    create_audit_log(
        db,
        action="diagram_unpublished",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Unpublished diagram `{record.title}`",
        metadata={"diagramId": record.id, **(actor_metadata or {})},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


def submit_diagram_for_review(db: Session, diagram_id: str, *, actor: str) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    now = datetime.now(timezone.utc)
    spec_json = dict(record.spec_json or {})
    spec_json["reviewStatus"] = "in_review"
    record.spec_json = spec_json
    flow_document = _ensure_flow_document(record.flow_document or {}, spec_json, title=record.title, objective=record.objective or "", owner=record.owner, source_page_ids=record.source_page_ids or [], source_ids=record.source_ids or [])
    flow_document["metadata"]["reviewStatus"] = "in_review"
    record.flow_document = flow_document
    record.status = "in_review"
    record.updated_at = now
    create_audit_log(
        db,
        action="diagram_submitted_for_review",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Submitted diagram `{record.title}` for review",
        metadata={"diagramId": record.id},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


def request_diagram_changes(db: Session, diagram_id: str, *, actor: str, comment: str | None = None) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    now = datetime.now(timezone.utc)
    spec_json = dict(record.spec_json or {})
    spec_json["reviewStatus"] = "changes_requested"
    review_notes = list(spec_json.get("reviewNotes", []))
    if comment:
        review_notes.append({"actor": actor, "comment": comment, "at": now.isoformat()})
    spec_json["reviewNotes"] = review_notes[-10:]
    record.spec_json = spec_json
    flow_document = _ensure_flow_document(record.flow_document or {}, spec_json, title=record.title, objective=record.objective or "", owner=record.owner, source_page_ids=record.source_page_ids or [], source_ids=record.source_ids or [])
    flow_document["metadata"]["reviewStatus"] = "changes_requested"
    flow_document["metadata"]["reviewNotes"] = review_notes[-10:]
    record.flow_document = flow_document
    record.status = "draft"
    record.updated_at = now
    create_audit_log(
        db,
        action="diagram_changes_requested",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Requested changes for diagram `{record.title}`",
        metadata={"diagramId": record.id, "comment": comment or ""},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)


def approve_diagram_review(db: Session, diagram_id: str, *, actor: str, comment: str | None = None) -> dict | None:
    record = get_diagram_by_id(db, diagram_id)
    if not record:
        return None
    now = datetime.now(timezone.utc)
    spec_json = dict(record.spec_json or {})
    spec_json["reviewStatus"] = "approved"
    review_notes = list(spec_json.get("reviewNotes", []))
    if comment:
        review_notes.append({"actor": actor, "comment": comment, "at": now.isoformat()})
    spec_json["reviewNotes"] = review_notes[-10:]
    record.spec_json = spec_json
    flow_document = _ensure_flow_document(record.flow_document or {}, spec_json, title=record.title, objective=record.objective or "", owner=record.owner, source_page_ids=record.source_page_ids or [], source_ids=record.source_ids or [])
    flow_document["metadata"]["reviewStatus"] = "approved"
    flow_document["metadata"]["reviewNotes"] = review_notes[-10:]
    record.flow_document = flow_document
    record.status = "draft"
    record.updated_at = now
    create_audit_log(
        db,
        action="diagram_review_approved",
        object_type="diagram",
        object_id=record.id,
        actor=actor,
        summary=f"Approved diagram review for `{record.title}`",
        metadata={"diagramId": record.id, "comment": comment or ""},
    )
    db.commit()
    db.refresh(record)
    return serialize_diagram(record, db)
