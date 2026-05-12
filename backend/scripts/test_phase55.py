from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skill_packages"
TEMP_PATH = SKILL_DIR / "phase55-skill.json"
sys.path.insert(0, str(ROOT))

from app.services.skills import approve_skill_package, add_skill_review_comment, get_skill_package, release_skill_package, submit_skill_for_review  # noqa: E402


def main() -> int:
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_PATH.write_text(
        json.dumps(
            {
                "id": "phase55-skill",
                "name": "Phase 55 Skill",
                "version": "0.1.0",
                "scope": "workspace",
                "status": "draft",
                "reviewStatus": "draft",
                "summary": "Temporary skill package for review lifecycle regression.",
                "description": "Used only by automated regression.",
                "capabilities": ["review handoff"],
                "tags": ["test"],
                "entryPoints": ["skills page"],
                "metadataJson": {"packageType": "workflow_pack"},
            },
            ensure_ascii=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        add_skill_review_comment("phase55-skill", actor="Tester", comment="Initial review note.")
        submit_skill_for_review("phase55-skill", actor="Tester", comment="Ready for reviewer.")
        approve_skill_package("phase55-skill", actor="Reviewer", comment="Approved for release.")
        released = release_skill_package("phase55-skill", actor="Reviewer", comment="Released to workspace registry.")
        current = get_skill_package("phase55-skill")
        payload = {
            "success": True,
            "reviewStatus": current.get("reviewStatus") if current else None,
            "status": current.get("status") if current else None,
            "historyTypes": [item.get("type") for item in (current.get("reviewHistory") or [])] if current else [],
            "releasedId": released.get("id") if released else None,
        }
        checks = [
            payload["reviewStatus"] == "released",
            payload["status"] == "released",
            payload["historyTypes"] == ["comment", "submit_review", "approve", "release"],
            payload["releasedId"] == "phase55-skill",
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 55 skill review lifecycle regression failed"
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 1
        sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    finally:
        if TEMP_PATH.exists():
            TEMP_PATH.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
