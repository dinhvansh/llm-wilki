from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Entity, Page, PageClaimLink, PageLink, PageSourceLink, ReviewItem, SourceChunk


def build_graph(
    db: Session,
    node_type: str = "all",
    status: str = "all",
    relation_types: list[str] | None = None,
    entity_types: list[str] | None = None,
    page_types: list[str] | None = None,
    collection_id: str | None = None,
    focus_id: str | None = None,
    local_mode: bool = False,
    show_orphans: bool = False,
    show_stale: bool = False,
    show_conflicts: bool = False,
    show_hubs: bool = False,
    limit: int = 250,
) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    relation_types = [value for value in (relation_types or []) if value]
    entity_types = [value for value in (entity_types or []) if value]
    page_types = [value for value in (page_types or []) if value]

    pages_query = db.query(Page)
    if status != "all":
        pages_query = pages_query.filter(Page.status == status)
    if page_types:
        pages_query = pages_query.filter(Page.page_type.in_(page_types))
    if collection_id:
        if collection_id == "standalone":
            pages_query = pages_query.filter(Page.collection_id.is_(None))
        else:
            pages_query = pages_query.filter(Page.collection_id == collection_id)
    pages = pages_query.limit(max(25, min(limit, 2000))).all()
    page_ids = {page.id for page in pages}
    page_lookup = {page.id: page for page in pages}
    page_source_map: dict[str, list[str]] = {}
    if page_ids:
        for page_id, source_id in db.query(PageSourceLink.page_id, PageSourceLink.source_id).filter(PageSourceLink.page_id.in_(page_ids)).all():
            page_source_map.setdefault(page_id, []).append(source_id)
    citation_counts: dict[str, int] = {}
    if page_ids:
        for page_id, in db.query(PageClaimLink.page_id).filter(PageClaimLink.page_id.in_(page_ids)).all():
            citation_counts[page_id] = citation_counts.get(page_id, 0) + 1
    conflict_page_ids = {
        page_id
        for (page_id,) in db.query(ReviewItem.page_id).filter(ReviewItem.issue_type == "conflict_detected").all()
        if page_id in page_ids
    }
    now = datetime.now(timezone.utc)

    if node_type in {"all", "page"}:
        nodes.extend(
            {
                "id": page.id,
                "type": "page",
                "label": page.title,
                "status": page.status,
                "pageType": page.page_type,
                "entityType": None,
                "description": page.summary,
                "url": f"/pages/{page.slug}",
                "sourceIds": sorted(page_source_map.get(page.id, [])),
                "collectionId": page.collection_id,
                "metrics": {
                    "degree": 0,
                    "backlinkCount": 0,
                    "relatedEntityCount": len(page.related_entity_ids or []),
                    "sourceCount": len(page_source_map.get(page.id, [])),
                    "citationCount": citation_counts.get(page.id, 0),
                    "hubScore": 0,
                    "clusterId": None,
                },
                "flags": {
                    "orphan": False,
                    "stale": page.status == "stale" or ((page.last_reviewed_at or page.last_composed_at).replace(tzinfo=timezone.utc) < now - timedelta(days=45)),
                    "conflict": page.id in conflict_page_ids,
                    "hub": False,
                    "recent": page.last_composed_at.replace(tzinfo=timezone.utc) > now - timedelta(days=7),
                },
            }
            for page in pages
        )

    node_index = {node["id"]: node for node in nodes}
    entity_ids: set[str] = set()
    if node_type in {"all", "entity"}:
        for page in pages:
            entity_ids.update(page.related_entity_ids or [])
        if entity_ids:
            entities_query = db.query(Entity).filter(Entity.id.in_(entity_ids))
            if entity_types:
                entities_query = entities_query.filter(Entity.entity_type.in_(entity_types))
            entities = entities_query.all()
            entity_ids = {entity.id for entity in entities}
            nodes.extend(
                {
                    "id": entity.id,
                    "type": "entity",
                    "label": entity.name,
                    "status": None,
                    "pageType": None,
                    "entityType": entity.entity_type,
                    "description": entity.description,
                    "url": None,
                    "sourceIds": [],
                    "collectionId": None,
                    "metrics": {"degree": 0, "backlinkCount": 0, "relatedEntityCount": 0, "sourceCount": 0, "citationCount": 0, "hubScore": 0, "clusterId": None},
                    "flags": {"orphan": False, "stale": False, "conflict": False, "hub": False, "recent": False},
                }
                for entity in entities
            )
            node_index.update({node["id"]: node for node in nodes if node["id"] not in node_index})

    for page_link in db.query(PageLink).all():
        if page_link.from_page_id in page_ids and page_link.to_page_id in page_ids:
            if relation_types and page_link.relation_type not in relation_types:
                continue
            edges.append(
                {
                    "id": page_link.id,
                    "source": page_link.from_page_id,
                    "target": page_link.to_page_id,
                    "relationType": page_link.relation_type,
                    "label": page_link.relation_type.replace("_", " "),
                    "semanticGroup": "page_link",
                }
            )

    if node_type in {"all", "entity"}:
        page_source_pairs = db.query(PageSourceLink.page_id, PageSourceLink.source_id).filter(PageSourceLink.page_id.in_(page_ids)).all()
        source_id_to_pages: dict[str, list[str]] = {}
        for page_id, source_id in page_source_pairs:
            source_id_to_pages.setdefault(source_id, []).append(page_id)

        if source_id_to_pages:
            chunks = db.query(SourceChunk).filter(SourceChunk.source_id.in_(list(source_id_to_pages))).all()
            for chunk in chunks:
                for entity_id in entity_ids:
                    if entity_id.lower() in (chunk.content or "").lower():
                        for page_id in source_id_to_pages.get(chunk.source_id, []):
                            if relation_types and "mentions" not in relation_types:
                                continue
                            edges.append(
                                {
                                    "id": f"edge-mentions-{page_id}-{entity_id}-{chunk.id}",
                                    "source": page_id,
                                    "target": entity_id,
                                    "relationType": "mentions",
                                    "label": "mentions",
                                    "semanticGroup": "entity_link",
                                }
                            )
                            if page_id in node_index:
                                node_index[page_id]["sourceIds"] = sorted(set(node_index[page_id]["sourceIds"]) | {chunk.source_id})
                            if entity_id in node_index:
                                node_index[entity_id]["sourceIds"] = sorted(set(node_index[entity_id]["sourceIds"]) | {chunk.source_id})

    deduped_edges: dict[str, dict] = {}
    for edge in edges:
        deduped_edges[edge["id"]] = edge
    edges = list(deduped_edges.values())

    if local_mode and focus_id:
        allowed_ids = {focus_id}
        for edge in edges:
            if edge["source"] == focus_id:
                allowed_ids.add(edge["target"])
            if edge["target"] == focus_id:
                allowed_ids.add(edge["source"])
        nodes = [node for node in nodes if node["id"] in allowed_ids]
        edges = [edge for edge in edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids]

    degree_counter: dict[str, int] = {}
    for edge in edges:
        degree_counter[edge["source"]] = degree_counter.get(edge["source"], 0) + 1
        degree_counter[edge["target"]] = degree_counter.get(edge["target"], 0) + 1
    for node in nodes:
        node["metrics"]["degree"] = degree_counter.get(node["id"], 0)
        node["metrics"]["hubScore"] = degree_counter.get(node["id"], 0) + node["metrics"].get("backlinkCount", 0) + node["metrics"].get("sourceCount", 0)
        if node["type"] == "page" and node["id"] in page_lookup:
            node["metrics"]["backlinkCount"] = sum(1 for edge in edges if edge["target"] == node["id"])
            node["metrics"]["hubScore"] = node["metrics"]["degree"] + node["metrics"]["backlinkCount"] + node["metrics"].get("sourceCount", 0)
        node["flags"]["orphan"] = node["metrics"]["degree"] == 0
        node["flags"]["hub"] = node["metrics"]["hubScore"] >= 4

    cluster_map: dict[str, int] = {}
    adjacency: dict[str, set[str]] = {node["id"]: set() for node in nodes}
    for edge in edges:
        if edge["source"] in adjacency and edge["target"] in adjacency:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])
    cluster_id = 0
    for node_id in adjacency:
        if node_id in cluster_map:
            continue
        cluster_id += 1
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in cluster_map:
                continue
            cluster_map[current] = cluster_id
            stack.extend(adjacency[current] - set(cluster_map))
    for node in nodes:
        node["metrics"]["clusterId"] = cluster_map.get(node["id"])

    if show_orphans or show_stale or show_conflicts or show_hubs:
        allowed_ids = {
            node["id"]
            for node in nodes
            if (show_orphans and node["flags"]["orphan"])
            or (show_stale and node["flags"]["stale"])
            or (show_conflicts and node["flags"]["conflict"])
            or (show_hubs and node["flags"]["hub"])
        }
        nodes = [node for node in nodes if node["id"] in allowed_ids]
        edges = [edge for edge in edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids]

    if not local_mode and len(nodes) > limit:
        nodes = sorted(nodes, key=lambda node: node["metrics"].get("hubScore", 0), reverse=True)[:limit]
        allowed_ids = {node["id"] for node in nodes}
        edges = [edge for edge in edges if edge["source"] in allowed_ids and edge["target"] in allowed_ids]

    node_details = {
        node["id"]: {
            "id": node["id"],
            "label": node["label"],
            "type": node["type"],
            "status": node.get("status"),
            "pageType": node.get("pageType"),
            "entityType": node.get("entityType"),
            "description": node.get("description"),
            "url": node.get("url"),
            "sourceIds": node.get("sourceIds", []),
            "collectionId": node.get("collectionId"),
            "metrics": node.get("metrics", {}),
            "flags": node.get("flags", {}),
            "connections": [
                {
                    "id": edge["id"],
                    "relationType": edge["relationType"],
                    "otherNodeId": edge["target"] if edge["source"] == node["id"] else edge["source"],
                }
                for edge in edges
                if edge["source"] == node["id"] or edge["target"] == node["id"]
            ],
        }
        for node in nodes
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "detailById": node_details,
        "meta": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "localMode": local_mode,
            "focusId": focus_id,
            "availableRelationTypes": sorted({edge["relationType"] for edge in edges}),
            "availablePageTypes": sorted({node["pageType"] for node in nodes if node.get("pageType")}),
            "availableEntityTypes": sorted({node["entityType"] for node in nodes if node.get("entityType")}),
            "collectionId": collection_id,
            "clusters": {
                "count": len(set(cluster_map.values())),
                "disconnectedCount": sum(1 for node_id, neighbors in adjacency.items() if not neighbors),
            },
            "analyticsFilters": {
                "showOrphans": show_orphans,
                "showStale": show_stale,
                "showConflicts": show_conflicts,
                "showHubs": show_hubs,
            },
        },
    }
