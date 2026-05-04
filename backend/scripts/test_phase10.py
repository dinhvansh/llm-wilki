from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase10.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.graph import build_graph  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        graph = build_graph(db)
        detail = graph["detailById"].get("page-002")
        hub_graph = build_graph(db, show_hubs=True)
        orphan_graph = build_graph(db, show_orphans=True)
        local_graph = build_graph(db, focus_id="page-002", local_mode=True)

        payload = {
            "success": True,
            "nodeCount": graph["meta"]["nodeCount"],
            "edgeCount": graph["meta"]["edgeCount"],
            "clusterCount": graph["meta"]["clusters"]["count"],
            "disconnectedCount": graph["meta"]["clusters"]["disconnectedCount"],
            "detailHasSourceCount": isinstance(detail["metrics"].get("sourceCount"), int) if detail else False,
            "detailHasCitationCount": isinstance(detail["metrics"].get("citationCount"), int) if detail else False,
            "detailHasFlags": bool(detail and detail.get("flags")),
            "hubFilterApplied": hub_graph["meta"]["analyticsFilters"]["showHubs"],
            "orphanFilterApplied": orphan_graph["meta"]["analyticsFilters"]["showOrphans"],
            "localMode": local_graph["meta"]["localMode"],
            "localFocusId": local_graph["meta"]["focusId"],
        }
        checks = [
            payload["nodeCount"] >= 1,
            payload["clusterCount"] >= 1,
            payload["detailHasSourceCount"],
            payload["detailHasCitationCount"],
            payload["detailHasFlags"],
            payload["hubFilterApplied"],
            payload["orphanFilterApplied"],
            payload["localMode"],
            payload["localFocusId"] == "page-002",
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 10 graph analytics checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
