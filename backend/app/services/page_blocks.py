from __future__ import annotations

import re
from copy import deepcopy
from uuid import uuid4

IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)\s*$")
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")
TODO_RE = re.compile(r"^\s*[-*]\s+\[(?P<checked>[xX ])\]\s+(?P<text>.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(?P<text>.+?)\s*$")


def _block_id() -> str:
    return f"blk-{uuid4().hex[:10]}"


def _text_block(block_type: str, text: str, **extra) -> dict:
    return {"id": _block_id(), "type": block_type, "text": text.strip(), **extra}


def markdown_to_blocks(content_md: str | None) -> list[dict]:
    content = (content_md or "").strip()
    if not content:
        return [{"id": _block_id(), "type": "paragraph", "text": ""}]

    blocks: list[dict] = []
    paragraph_lines: list[str] = []
    bullet_items: list[str] = []
    todo_items: list[dict] = []
    quote_lines: list[str] = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            blocks.append(_text_block("paragraph", "\n".join(paragraph_lines)))
            paragraph_lines = []

    def flush_bullets():
        nonlocal bullet_items
        if bullet_items:
            blocks.append({"id": _block_id(), "type": "bullet_list", "items": bullet_items[:]})
            bullet_items = []

    def flush_todos():
        nonlocal todo_items
        if todo_items:
            blocks.append({"id": _block_id(), "type": "todo_list", "items": deepcopy(todo_items)})
            todo_items = []

    def flush_quotes():
        nonlocal quote_lines
        if quote_lines:
            blocks.append(_text_block("quote", "\n".join(quote_lines)))
            quote_lines = []

    def flush_all():
        flush_paragraph()
        flush_bullets()
        flush_todos()
        flush_quotes()

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_all()
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            flush_all()
            alt = image_match.group("alt").strip()
            url = image_match.group("url").strip()
            blocks.append(
                {
                    "id": _block_id(),
                    "type": "image",
                    "url": url,
                    "caption": alt,
                    "alt": alt,
                }
            )
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush_all()
            blocks.append(
                {
                    "id": _block_id(),
                    "type": "heading",
                    "level": len(heading_match.group("hashes")),
                    "text": heading_match.group("text").strip(),
                }
            )
            continue

        todo_match = TODO_RE.match(stripped)
        if todo_match:
            flush_paragraph()
            flush_bullets()
            flush_quotes()
            todo_items.append(
                {
                    "text": todo_match.group("text").strip(),
                    "checked": todo_match.group("checked").lower() == "x",
                }
            )
            continue

        bullet_match = BULLET_RE.match(stripped)
        if bullet_match:
            flush_paragraph()
            flush_todos()
            flush_quotes()
            bullet_items.append(bullet_match.group("text").strip())
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_bullets()
            flush_todos()
            quote_lines.append(stripped.removeprefix(">").strip())
            continue

        flush_bullets()
        flush_todos()
        flush_quotes()
        paragraph_lines.append(line)

    flush_all()
    return blocks or [{"id": _block_id(), "type": "paragraph", "text": ""}]


def sanitize_blocks(content_json: list[dict] | None) -> list[dict]:
    if not isinstance(content_json, list):
        return [{"id": _block_id(), "type": "paragraph", "text": ""}]

    sanitized: list[dict] = []
    for raw in content_json:
        if not isinstance(raw, dict):
            continue
        block_type = str(raw.get("type") or "paragraph")
        block_id = str(raw.get("id") or _block_id())
        if block_type == "heading":
            text = str(raw.get("text") or "").strip()
            level = int(raw.get("level") or 1)
            sanitized.append({"id": block_id, "type": "heading", "level": min(max(level, 1), 6), "text": text})
        elif block_type == "image":
            url = str(raw.get("url") or "").strip()
            if not url:
                continue
            caption = str(raw.get("caption") or "").strip()
            alt = str(raw.get("alt") or caption).strip()
            asset_id = raw.get("assetId")
            sanitized.append({"id": block_id, "type": "image", "url": url, "caption": caption, "alt": alt, "assetId": asset_id})
        elif block_type == "bullet_list":
            items = [str(item).strip() for item in raw.get("items") or [] if str(item).strip()]
            sanitized.append({"id": block_id, "type": "bullet_list", "items": items or [""]})
        elif block_type == "todo_list":
            items = []
            for item in raw.get("items") or []:
                if isinstance(item, dict):
                    text = str(item.get("text") or "").strip()
                    items.append({"text": text, "checked": bool(item.get("checked"))})
            sanitized.append({"id": block_id, "type": "todo_list", "items": items or [{"text": "", "checked": False}]})
        elif block_type == "quote":
            sanitized.append({"id": block_id, "type": "quote", "text": str(raw.get("text") or "").strip()})
        else:
            sanitized.append({"id": block_id, "type": "paragraph", "text": str(raw.get("text") or "").strip()})

    return sanitized or [{"id": _block_id(), "type": "paragraph", "text": ""}]


def blocks_to_markdown(content_json: list[dict] | None) -> str:
    blocks = sanitize_blocks(content_json)
    lines: list[str] = []
    for block in blocks:
        block_type = block.get("type")
        if block_type == "heading":
            lines.append(f"{'#' * int(block.get('level', 1))} {str(block.get('text') or '').strip()}".rstrip())
        elif block_type == "image":
            alt = str(block.get("caption") or block.get("alt") or "image").strip()
            lines.append(f"![{alt}]({str(block.get('url') or '').strip()})")
        elif block_type == "bullet_list":
            lines.extend(f"- {item}" for item in (block.get("items") or []))
        elif block_type == "todo_list":
            lines.extend(f"- [{'x' if item.get('checked') else ' '}] {item.get('text', '').strip()}".rstrip() for item in (block.get("items") or []))
        elif block_type == "quote":
            quote_text = str(block.get("text") or "").splitlines() or [""]
            lines.extend(f"> {line}".rstrip() for line in quote_text)
        else:
            lines.append(str(block.get("text") or "").rstrip())
        lines.append("")
    return "\n".join(lines).strip()


def normalize_page_document(content_md: str | None, content_json: list[dict] | None) -> tuple[str, list[dict]]:
    if content_json:
        normalized_blocks = sanitize_blocks(content_json)
        normalized_md = (content_md or "").strip() or blocks_to_markdown(normalized_blocks)
        return normalized_md, normalized_blocks
    normalized_md = (content_md or "").strip()
    normalized_blocks = markdown_to_blocks(normalized_md)
    return normalized_md, normalized_blocks
