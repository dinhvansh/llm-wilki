from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "test_phase16.db"
MIGRATION_DB_PATH = ROOT / "test_phase16_migration.db"
for path in [DB_PATH, MIGRATION_DB_PATH]:
    if path.exists():
        path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AUTO_SEED_DEMO_DATA"] = "true"
os.environ["JOB_QUEUE_BACKEND"] = "database"
os.environ["DEBUG"] = "true"
sys.path.insert(0, str(ROOT))

from app.core.bootstrap import init_database  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.services.graph import build_graph  # noqa: E402
from app.services.lint import run_lint  # noqa: E402
from app.services.query import ask, search  # noqa: E402
from app.services.settings import serialize_runtime_settings, update_runtime_settings  # noqa: E402


def run_migration_smoke() -> bool:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{MIGRATION_DB_PATH.as_posix()}"
    env["JOB_QUEUE_BACKEND"] = "database"
    env["DEBUG"] = "true"
    result = subprocess.run(
        [sys.executable, "-c", "from alembic.config import main; main()", "-c", "alembic.ini", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return False
    return MIGRATION_DB_PATH.exists()


def main() -> int:
    migration_ok = run_migration_smoke()
    benchmark = subprocess.run(
        [sys.executable, "scripts/benchmark_retrieval.py"],
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=120,
    )
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=True)
        settings = serialize_runtime_settings(db)
        settings.update({"searchResultLimit": 3, "graphNodeLimit": 4, "lintPageLimit": 3})
        updated = update_runtime_settings(db, settings)

        results = search(db, "hybrid retrieval citation", limit=50)
        answer = ask(db, "What does the wiki say about hybrid retrieval?")
        graph = build_graph(db, limit=4)
        lint = run_lint(db, page_size=5, max_pages=3)

        payload = {
            "success": True,
            "migrationOk": migration_ok,
            "settingsLimits": {
                "searchResultLimit": updated["searchResultLimit"],
                "graphNodeLimit": updated["graphNodeLimit"],
                "lintPageLimit": updated["lintPageLimit"],
            },
            "searchCount": len(results),
            "searchHasDiagnostics": bool(results and results[0].get("diagnostics", {}).get("finalScore") is not None),
            "askHasDiagnostics": bool(answer.get("diagnostics", {}).get("topChunks")),
            "askCitations": len(answer["citations"]),
            "graphNodeCount": len(graph["nodes"]),
            "lintScannedPages": lint["summary"].get("scannedPages"),
            "benchmarkOk": benchmark.returncode == 0,
        }
        checks = [
            payload["migrationOk"],
            payload["settingsLimits"]["searchResultLimit"] == 3,
            payload["searchCount"] <= 3,
            payload["searchHasDiagnostics"],
            payload["askHasDiagnostics"],
            payload["askCitations"] >= 1,
            payload["graphNodeCount"] <= 4,
            payload["lintScannedPages"] <= 3,
            payload["benchmarkOk"],
        ]
        if not all(checks):
            payload["success"] = False
            payload["benchmarkStdout"] = benchmark.stdout
            payload["benchmarkStderr"] = benchmark.stderr
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

