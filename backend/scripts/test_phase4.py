from __future__ import annotations

import json
import urllib.request


API_BASE = "http://127.0.0.1:8000/api"


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def main() -> int:
    lint_payload = fetch_json(f"{API_BASE}/lint?page=1&pageSize=50")
    graph_payload = fetch_json(f"{API_BASE}/graph?nodeType=all&localMode=true&focusId=page-002")

    lint_items = lint_payload.get("data", [])
    graph_nodes = graph_payload.get("nodes", [])
    graph_edges = graph_payload.get("edges", [])
    meta = graph_payload.get("meta", {})
    detail_by_id = graph_payload.get("detailById", {})

    payload = {
        "success": True,
        "lintIssueCount": lint_payload.get("total", 0),
        "hasLintSummary": isinstance(lint_payload.get("summary"), dict),
        "hasSixPlusRules": len((lint_payload.get("summary") or {}).get("rules", [])) >= 6,
        "graphNodeCount": len(graph_nodes),
        "graphEdgeCount": len(graph_edges),
        "graphLocalMode": bool(meta.get("localMode")),
        "hasGraphMeta": isinstance(meta, dict),
        "hasGraphDetailById": isinstance(detail_by_id, dict) and bool(detail_by_id),
    }

    if not payload["hasLintSummary"] or not payload["hasSixPlusRules"]:
        payload["success"] = False
        payload["message"] = "Lint API does not expose expected framework and rules"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if not graph_nodes or not graph_edges:
        payload["success"] = False
        payload["message"] = "Graph API returned empty graph"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if not payload["graphLocalMode"] or not payload["hasGraphMeta"] or not payload["hasGraphDetailById"]:
        payload["success"] = False
        payload["message"] = "Graph API does not expose upgraded local/detail model"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
