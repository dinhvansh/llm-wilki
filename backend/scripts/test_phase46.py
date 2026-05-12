from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMP_DIR = ROOT / "evals" / "_tmp"
EXPORT_PATH = TEMP_DIR / "exported_eval_dataset.json"
IMPORT_PATH = TEMP_DIR / "import_eval_dataset.json"
DATASET_PATH = ROOT / "evals" / "golden_dataset.json"
BACKUP_PATH = TEMP_DIR / "golden_dataset.backup.json"
sys.path.insert(0, str(ROOT))

from scripts.manage_eval_dataset import export_dataset, import_dataset  # noqa: E402


def main() -> int:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DATASET_PATH, BACKUP_PATH)
    try:
        export_dataset(EXPORT_PATH)
        exported = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
        exported["syntheticCases"]["unsupportedClaim"] = "Synthetic import/export validation."
        IMPORT_PATH.write_text(json.dumps(exported, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        import_dataset(IMPORT_PATH)
        imported = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        payload = {
            "success": True,
            "exportExists": EXPORT_PATH.exists(),
            "importedUnsupportedClaim": imported.get("syntheticCases", {}).get("unsupportedClaim"),
            "caseCount": len(imported.get("cases", [])),
            "behaviorCaseCount": len(imported.get("behaviorCases", [])),
        }
        checks = [
            payload["exportExists"],
            payload["importedUnsupportedClaim"] == "Synthetic import/export validation.",
            payload["caseCount"] >= 1,
            payload["behaviorCaseCount"] >= 1,
        ]
        if not all(checks):
            payload["success"] = False
            payload["message"] = "Phase 46 eval dataset import/export regression failed"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        shutil.copyfile(BACKUP_PATH, DATASET_PATH)
        shutil.rmtree(TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
