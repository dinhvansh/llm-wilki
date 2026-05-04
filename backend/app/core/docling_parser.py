from __future__ import annotations

from pathlib import Path

from app.config import settings


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

    ocr_options = TesseractCliOcrOptions(
        lang=settings.DOCLING_OCR_LANGS,
        force_full_page_ocr=settings.DOCLING_FORCE_FULL_PAGE_OCR,
        path=settings.DOCLING_TESSDATA_PATH or None,
        tesseract_cmd=settings.DOCLING_TESSERACT_CMD,
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
            "tessdataPath": settings.DOCLING_TESSDATA_PATH,
            "tesseractCommand": settings.DOCLING_TESSERACT_CMD,
            "pageCount": len(getattr(document, "pages", {}) or {}),
        },
    }
    return markdown, metadata
