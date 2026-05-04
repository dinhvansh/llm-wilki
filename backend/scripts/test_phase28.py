from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.core.connectors import get_connector_capability
from app.core.ingest import parse_document


def main() -> None:
    try:
        langs_output = subprocess.check_output(["tesseract", "--list-langs"], text=True, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        print(
            {
                "success": True,
                "skipped": True,
                "reason": "tesseract binary is not installed or not on PATH in this local environment",
            }
        )
        return

    assert "eng" in langs_output, langs_output
    assert "vie" in langs_output, langs_output

    assert settings.DOCLING_OCR_ENGINE == "tesseract_cli"
    assert "vie" in settings.DOCLING_OCR_LANGS

    capability = get_connector_capability("image_ocr")
    assert capability is not None
    assert capability.label == "Image OCR"

    sample = Path("phase28-docling-test.md")
    sample.write_text("# Quy trinh\n\nBuoc 1: Tiep nhan yeu cau.\n\nBuoc 2: Phe duyet.", encoding="utf-8")
    try:
        parsed = parse_document(sample, "text/markdown", "markdown")
        assert parsed.metadata.get("parser") == "docling", parsed.metadata
        assert parsed.metadata.get("docling", {}).get("ocrEngine") == "tesseract_cli", parsed.metadata
        assert "Quy trinh" in parsed.text
    finally:
        sample.unlink(missing_ok=True)

    print(
        {
            "success": True,
            "doclingParser": True,
            "ocrEngine": settings.DOCLING_OCR_ENGINE,
            "ocrLangs": settings.DOCLING_OCR_LANGS,
            "imageConnector": capability.label,
        }
    )


if __name__ == "__main__":
    main()
