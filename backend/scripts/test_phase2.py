from __future__ import annotations

import json
import time
import urllib.request


API_BASE = "http://127.0.0.1:8000/api"


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def post_empty(url: str) -> dict:
    request = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def main() -> int:
    sources = fetch_json(f"{API_BASE}/sources?page=1&pageSize=20")
    items = sources.get("data", [])
    docx_source = next((item for item in items if item.get("sourceType") == "docx"), None)
    if not docx_source:
        print(json.dumps({"success": False, "message": "No DOCX source found to verify Phase 2 pipeline"}))
        return 1

    source_id = docx_source["id"]
    job = post_empty(f"{API_BASE}/sources/{source_id}/rebuild")
    job_id = job["jobId"]

    final_status = None
    for _ in range(60):
        current = fetch_json(f"{API_BASE}/jobs/{job_id}")
        final_status = current["status"]
        if final_status in {"completed", "failed"}:
            break
        time.sleep(2)

    source = fetch_json(f"{API_BASE}/sources/{source_id}")
    metadata = source.get("metadataJson", {})
    stage_results = metadata.get("pipelineStages", [])
    page_type_candidates = metadata.get("pageTypeCandidates", [])
    stage_names = [stage.get("name") for stage in stage_results]

    payload = {
        "success": final_status == "completed",
        "sourceId": source_id,
        "jobStatus": final_status,
        "stageNames": stage_names,
        "pageTypeCandidates": page_type_candidates,
        "chunkCount": metadata.get("chunkCount"),
    }

    required_stages = {
        "parse",
        "chunk",
        "summarize",
        "extract_entities",
        "extract_claims",
        "classify_page_types",
    }

    if final_status != "completed":
        payload["message"] = "Rebuild job did not complete successfully"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if not required_stages.issubset(stage_names):
        payload["success"] = False
        payload["message"] = "Missing required pipeline stages"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if not page_type_candidates:
        payload["success"] = False
        payload["message"] = "No page type candidates generated"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
