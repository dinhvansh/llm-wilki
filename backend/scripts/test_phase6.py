from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase6.db"
if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.collections import assign_source_collection, create_collection, delete_collection, list_collections, update_collection  # noqa: E402
from app.services.graph import build_graph  # noqa: E402
from app.services.pages import list_pages  # noqa: E402
from app.services.sources import list_sources  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)

        collections = list_collections(db)
        engineering = next((item for item in collections if item["id"] == "col-002"), None)
        engineering_sources = list_sources(db, collection_id="col-002", page_size=50)
        engineering_pages = list_pages(db, collection_id="col-002", page_size=50)
        standalone_sources = list_sources(db, collection_id="standalone", page_size=50)
        graph_payload = build_graph(db, collection_id="col-002")

        assignment = assign_source_collection(db, "src-004", "col-001")
        moved_source = list_sources(db, collection_id="col-001", search="API Reference", page_size=50)
        created = create_collection(db, "Temporary Test Collection", "Created by Phase 6 test", "slate")
        updated = update_collection(db, created["id"], name="Temporary Test Collection Updated")
        deleted = delete_collection(db, created["id"])

        payload = {
            "success": True,
            "collectionCount": len(collections),
            "hasEngineeringCollection": engineering is not None,
            "engineeringSourceCount": engineering_sources["total"],
            "engineeringPageCount": engineering_pages["total"],
            "standaloneSourceCount": standalone_sources["total"],
            "graphNodeCountForEngineering": len(graph_payload.get("nodes", [])),
            "graphCollectionId": (graph_payload.get("meta") or {}).get("collectionId"),
            "assignment": assignment,
            "movedSourceCount": moved_source["total"],
            "createdCollectionId": created["id"],
            "updatedCollectionName": updated["name"] if updated else None,
            "deletedCollection": deleted,
        }

        checks = [
            payload["collectionCount"] >= 3,
            payload["hasEngineeringCollection"],
            payload["engineeringSourceCount"] >= 1,
            payload["engineeringPageCount"] >= 1,
            payload["graphNodeCountForEngineering"] >= 1,
            payload["graphCollectionId"] == "col-002",
            payload["assignment"] == {"sourceId": "src-004", "collectionId": "col-001"},
            payload["movedSourceCount"] == 1,
            bool(payload["createdCollectionId"]),
            payload["updatedCollectionName"] == "Temporary Test Collection Updated",
            payload["deletedCollection"] is True,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 6 collections checks failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
