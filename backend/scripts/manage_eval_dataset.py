from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "evals" / "golden_dataset.json"


def validate_dataset(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Dataset payload must be a JSON object.")
    if not isinstance(payload.get("cases"), list):
        raise ValueError("Dataset must include a list `cases`.")
    if not isinstance(payload.get("behaviorCases"), list):
        raise ValueError("Dataset must include a list `behaviorCases`.")
    if not isinstance(payload.get("syntheticCases"), dict):
        raise ValueError("Dataset must include an object `syntheticCases`.")


def export_dataset(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DATASET_PATH, output_path)


def import_dataset(input_path: Path) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    validate_dataset(payload)
    DATASET_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import/export Ask AI eval dataset.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export current eval dataset.")
    export_parser.add_argument("--output", required=True, help="Path to output JSON file.")

    import_parser = subparsers.add_parser("import", help="Import eval dataset from JSON file.")
    import_parser.add_argument("--input", required=True, help="Path to input JSON file.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    if args.command == "export":
        export_dataset(Path(args.output).resolve())
        print(json.dumps({"success": True, "command": "export", "output": args.output}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "import":
        import_dataset(Path(args.input).resolve())
        print(json.dumps({"success": True, "command": "import", "input": args.input}, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
