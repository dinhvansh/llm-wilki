from __future__ import annotations

import json
import urllib.request


API_BASE = "http://127.0.0.1:8000/api"


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def main() -> int:
    review_queue = fetch_json(f"{API_BASE}/review-items?page=1&pageSize=20")
    pages = fetch_json(f"{API_BASE}/pages?page=1&pageSize=10")

    queue_items = review_queue.get("data", [])
    page_items = pages.get("data", [])
    page_with_backlinks = next((item for item in page_items if isinstance(item.get("backlinks"), list)), None)
    item_with_suggestions = next((item for item in queue_items if isinstance(item.get("suggestions"), list)), None)
    item_with_change_set = next((item for item in queue_items if isinstance(item.get("changeSet"), dict)), None)
    item_with_page_context = next((item for item in queue_items if isinstance(item.get("pageContext"), dict)), None)

    payload = {
        "success": True,
        "reviewItemCount": len(queue_items),
        "hasVirtualItem": any(bool(item.get("isVirtual")) for item in queue_items),
        "hasSuggestions": bool(item_with_suggestions and len(item_with_suggestions.get("suggestions", [])) >= 0),
        "hasBacklinksInPagePayload": bool(page_with_backlinks is not None),
        "hasChangeSet": bool(item_with_change_set),
        "hasPageContext": bool(item_with_page_context),
        "sampleReviewItemId": item_with_suggestions.get("id") if item_with_suggestions else None,
        "sampleSuggestionCount": len(item_with_suggestions.get("suggestions", [])) if item_with_suggestions else 0,
        "sampleBacklinkCount": len(page_with_backlinks.get("backlinks", [])) if page_with_backlinks else 0,
        "sampleDiffLineCount": len(item_with_change_set.get("changeSet", {}).get("diffLines", [])) if item_with_change_set else 0,
    }

    if not queue_items:
        payload["success"] = False
        payload["message"] = "Review queue is empty"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if page_with_backlinks is None:
        payload["success"] = False
        payload["message"] = "Pages payload does not expose backlinks"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if item_with_suggestions is None:
        payload["success"] = False
        payload["message"] = "Review payload does not expose suggestions"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if item_with_change_set is None or item_with_page_context is None:
        payload["success"] = False
        payload["message"] = "Review payload does not expose refactored page/update schema"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
