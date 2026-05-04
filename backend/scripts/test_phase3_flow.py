from __future__ import annotations

import json
import time
import urllib.request
from uuid import uuid4


API_BASE = "http://127.0.0.1:8000/api"


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def post_json(url: str, payload: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload or {}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def post_multipart_file(url: str, filename: str, content: str, mime_type: str = "text/markdown") -> dict:
    boundary = f"----CodexBoundary{uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + content.encode("utf-8") + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def post_empty(url: str) -> dict:
    request = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def wait_for_job(job_id: str) -> str:
    final_status = "unknown"
    for _ in range(60):
        current = fetch_json(f"{API_BASE}/jobs/{job_id}")
        final_status = current["status"]
        if final_status in {"completed", "failed"}:
            return final_status
        time.sleep(2)
    return final_status


def main() -> int:
    sources = fetch_json(f"{API_BASE}/sources?page=1&pageSize=20")
    rebuild_source = next((source for source in sources.get("data", []) if source.get("sourceType") == "docx"), None)
    if not rebuild_source:
        print(json.dumps({"success": False, "message": "No rebuild source available for Phase 3 flow test"}, ensure_ascii=False, indent=2))
        return 1

    decision_upload = post_multipart_file(
        f"{API_BASE}/sources/upload",
        f"phase3-flow-approve-{uuid4().hex[:6]}.md",
        "# Review Flow Approval\n\nThis temporary source is used to verify reject and approve actions in the review workflow.\n\nIt contains a concise internal policy note for testing.",
    )
    merge_upload = post_multipart_file(
        f"{API_BASE}/sources/upload",
        f"phase3-flow-merge-{uuid4().hex[:6]}.md",
        "# Document Processing Pipeline\n\nThe document processing pipeline and LLM integration standards are linked in this temporary review source.\n\nThis note exists to trigger merge suggestions against existing pages like Document Processing Pipeline and LLM Integration Standards.",
    )

    decision_job_status = wait_for_job(decision_upload["metadataJson"]["jobId"])
    merge_job_status = wait_for_job(merge_upload["metadataJson"]["jobId"])
    if decision_job_status != "completed" or merge_job_status != "completed":
        print(
            json.dumps(
                {
                    "success": False,
                    "message": "Seed uploads did not complete",
                    "decisionJobStatus": decision_job_status,
                    "mergeJobStatus": merge_job_status,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    review_queue = fetch_json(f"{API_BASE}/review-items?page=1&pageSize=50")
    items = review_queue.get("data", [])
    decision_source_id = decision_upload["id"]
    merge_source_id = merge_upload["id"]
    decision_target = next((item for item in items if decision_source_id in item.get("sourceIds", [])), None)
    merge_candidate = next((item for item in items if merge_source_id in item.get("sourceIds", [])), None)

    payload = {
        "success": True,
        "queueCount": len(items),
        "mergeTested": False,
        "approveTested": False,
        "rejectTested": False,
        "rebuildTested": False,
    }

    if not items or not decision_target or not merge_candidate:
        payload["success"] = False
        payload["message"] = "Review queue does not have enough coverage for flow test"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    reject_result = post_json(f"{API_BASE}/review-items/{decision_target['id']}/reject", {"reason": "phase3 flow reject check"})
    payload["rejectTested"] = bool(reject_result.get("success"))

    approve_result = post_empty(f"{API_BASE}/review-items/{decision_target['id']}/approve")
    approved_page = approve_result.get("page", {})
    payload["approveTested"] = bool(approve_result.get("success"))
    payload["approvedPageStatus"] = approved_page.get("status")

    merge_target = next(
        (
            suggestion.get("targetId")
            for suggestion in merge_candidate.get("suggestions", [])
            if suggestion.get("type") == "page_match" and suggestion.get("targetId")
        ),
        None,
    )
    if not merge_target:
        payload["success"] = False
        payload["message"] = "Merge candidate did not produce any page_match suggestion"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    merge_result = post_json(
        f"{API_BASE}/review-items/{merge_candidate['id']}/merge",
        {"targetPageId": merge_target, "comment": "phase3 flow merge check"},
    )
    payload["mergeTested"] = bool(merge_result.get("success"))
    payload["mergeTargetPageId"] = merge_result.get("targetPageId")
    payload["archivedPageStatus"] = merge_result.get("archivedPage", {}).get("status")

    rebuild_result = post_empty(f"{API_BASE}/sources/{rebuild_source['id']}/rebuild")
    job_status = wait_for_job(rebuild_result["jobId"])
    payload["rebuildTested"] = job_status == "completed"
    payload["rebuildJobStatus"] = job_status
    payload["rebuildSourceId"] = rebuild_source["id"]

    refreshed_queue = fetch_json(f"{API_BASE}/review-items?page=1&pageSize=50")
    payload["remainingQueueCount"] = refreshed_queue.get("total")

    if payload["approvedPageStatus"] != "published":
        payload["success"] = False
        payload["message"] = "Approve flow did not publish the page"
    elif payload["archivedPageStatus"] != "archived":
        payload["success"] = False
        payload["message"] = "Merge flow did not archive the source page"
    elif job_status != "completed":
        payload["success"] = False
        payload["message"] = "Rebuild flow did not complete successfully"

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
