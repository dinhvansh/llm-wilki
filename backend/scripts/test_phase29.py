from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingest import split_into_structured_chunks, split_into_window_chunks
from app.schemas.settings import SettingsPayload


SAMPLE = """# Quy trinh tiep nhan

Mo ta tong quan ve quy trinh tiep nhan va xu ly tai lieu nghiep vu.

## Buoc chuan bi

1. Tiep nhan yeu cau tu bo phan kinh doanh.
2. Xac nhan tai lieu nguon, pham vi, va owner.
3. Tao phien ban draft de review.

| Truong | Mo ta |
| --- | --- |
| Owner | Business Analyst |
| Reviewer | Domain Lead |

## Xu ly chi tiet

Doan van nay duoc viet dai hon de chunker phai chia thanh nhieu doan nho hon nhung van giu context trong cung heading. He thong can tranh cat giua bang bieu va danh sach, dong thoi van ton trong gioi han kich thuoc chunk cho prose de downstream claim va BPM extractor co du lieu nhat quan hon.

Doan van thu hai tiep tuc giai thich cac dieu kien ngoai le, cach xu ly khi tai lieu thieu thong tin, va cach ghi lai open questions cho reviewer thay vi tu doan bo sung noi dung.
"""


def main() -> None:
    structured = split_into_structured_chunks(SAMPLE, max_words=45, overlap=8)
    window = split_into_window_chunks(SAMPLE, max_words=45, overlap=8)

    assert len(structured) >= 4, structured
    assert any("blockTypes" in chunk.get("metadata", {}) for chunk in structured), structured
    assert any("list" in chunk.get("metadata", {}).get("blockTypes", []) for chunk in structured), structured
    assert any("table" in chunk.get("metadata", {}).get("blockTypes", []) for chunk in structured), structured
    assert any(chunk.get("metadata", {}).get("headingPath") == ["Quy trinh tiep nhan", "Buoc chuan bi"] for chunk in structured), structured
    assert all(chunk["metadata"]["chunkingMode"] == "structured" for chunk in structured), structured
    assert any(chunk["token_count"] > 0 for chunk in structured), structured
    assert all("metadata" not in chunk for chunk in window), window

    payload = SettingsPayload(chunkMode="structured")
    assert payload.chunkMode == "structured"

    print(
        {
            "structuredChunkCount": len(structured),
            "windowChunkCount": len(window),
            "structuredBlockTypes": [chunk["metadata"]["blockTypes"] for chunk in structured],
        }
    )


if __name__ == "__main__":
    main()
