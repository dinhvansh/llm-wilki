from __future__ import annotations

import os
from pathlib import Path
import shutil

from app.config import settings


def _workspace_local_tessdata_dir() -> Path:
    return Path(__file__).resolve().parents[2] / ".local" / "tessdata"


def resolve_tesseract_command() -> str:
    configured = str(settings.DOCLING_TESSERACT_CMD or "").strip()
    candidates: list[str] = []
    if configured:
        candidates.append(configured)
        resolved_configured = shutil.which(configured)
        if resolved_configured:
            candidates.append(resolved_configured)
    candidates.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    )

    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(candidate).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if Path(normalized).exists():
            return normalized
    return configured or "tesseract"


def resolve_tessdata_path(tesseract_cmd: str | None = None) -> str | None:
    configured = str(settings.DOCLING_TESSDATA_PATH or "").strip()
    if configured and Path(configured).exists():
        return configured

    local_override = _workspace_local_tessdata_dir()
    if local_override.exists():
        return str(local_override)

    env_override = str(os.environ.get("TESSDATA_PREFIX") or "").strip()
    if env_override and Path(env_override).exists():
        return env_override

    resolved_cmd = str(tesseract_cmd or "").strip()
    if resolved_cmd and Path(resolved_cmd).exists():
        sibling_tessdata = Path(resolved_cmd).resolve().parent / "tessdata"
        if sibling_tessdata.exists():
            return str(sibling_tessdata)

    return None


def parse_with_docling(path: Path, mime_type: str, source_type: str) -> tuple[str, dict]:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import (
            DocumentConverter,
            HTMLFormatOption,
            ImageFormatOption,
            MarkdownFormatOption,
            PdfFormatOption,
            WordFormatOption,
        )
    except ImportError as exc:
        raise ValueError(
            "Docling parser is not available. Install Docling and OCR dependencies in the backend environment."
        ) from exc

    resolved_tesseract_cmd = resolve_tesseract_command()
    resolved_tessdata_path = resolve_tessdata_path(resolved_tesseract_cmd)

    ocr_options = TesseractCliOcrOptions(
        lang=settings.DOCLING_OCR_LANGS,
        force_full_page_ocr=settings.DOCLING_FORCE_FULL_PAGE_OCR,
        path=resolved_tessdata_path,
        tesseract_cmd=resolved_tesseract_cmd,
        psm=settings.DOCLING_TESSERACT_PSM,
    )

    paginated_pipeline = PdfPipelineOptions()
    paginated_pipeline.do_ocr = source_type in {"pdf", "image_ocr"}
    paginated_pipeline.do_table_structure = True
    paginated_pipeline.ocr_options = ocr_options

    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.MD,
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=paginated_pipeline),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=paginated_pipeline),
            InputFormat.DOCX: WordFormatOption(),
            InputFormat.HTML: HTMLFormatOption(),
            InputFormat.MD: MarkdownFormatOption(),
        },
    )

    try:
        result = converter.convert(path)
    except Exception as exc:
        raise ValueError(f"Docling failed to parse `{path.name}`: {exc}") from exc

    document = result.document
    if document is None:
        raise ValueError(f"Docling returned no document for `{path.name}`.")
    markdown = document.export_to_markdown().strip()
    metadata = {
        "parser": "docling",
        "docling": {
            "inputFormat": source_type,
            "mimeType": mime_type,
            "ocrEngine": settings.DOCLING_OCR_ENGINE,
            "ocrLanguages": settings.DOCLING_OCR_LANGS,
            "forceFullPageOcr": settings.DOCLING_FORCE_FULL_PAGE_OCR,
            "tessdataPath": resolved_tessdata_path,
            "tesseractCommand": resolved_tesseract_cmd,
            "pageCount": len(getattr(document, "pages", {}) or {}),
        },
    }
    return markdown, metadata
