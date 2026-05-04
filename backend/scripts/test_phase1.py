from __future__ import annotations

import json
import urllib.request


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.load(response)


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def main() -> int:
    settings = fetch_json("http://127.0.0.1:8000/api/settings")
    ask_payload = post_json("http://127.0.0.1:8000/api/ask", {"question": "National Account Relationship duoc dung de lam gi?"})

    payload = {
        "success": True,
        "embeddingProvider": settings.get("embeddingProvider"),
        "embeddingModel": settings.get("embeddingModel"),
        "citations": len(ask_payload.get("citations", [])),
        "hasSpanCitation": bool(ask_payload.get("citations") and isinstance(ask_payload["citations"][0].get("sourceSpanStart"), int)),
        "hasIllustrations": "Related Illustrations" in ask_payload.get("answer", ""),
        "confidence": ask_payload.get("confidence"),
    }

    if not payload["embeddingModel"]:
        payload["success"] = False
        payload["message"] = "Embedding model is not configured"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if not payload["hasSpanCitation"]:
        payload["success"] = False
        payload["message"] = "Citation span metadata is missing"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
