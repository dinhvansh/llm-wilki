from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models import Source, SourceArtifactRecord, StorageObject


def find_orphan_storage_objects(db):
    rows = db.query(StorageObject).filter(StorageObject.lifecycle_state == "active").all()
    orphans: list[StorageObject] = []
    for row in rows:
        if row.source_id and not db.query(Source.id).filter(Source.id == row.source_id).first():
            orphans.append(row)
            continue
        if row.artifact_id and not db.query(SourceArtifactRecord.id).filter(SourceArtifactRecord.id == row.artifact_id).first():
            orphans.append(row)
    return orphans


def main() -> None:
    parser = argparse.ArgumentParser(description="Find or mark orphaned storage object records.")
    parser.add_argument("--apply", action="store_true", help="Mark detected orphan records as orphaned. Default is dry-run.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        orphans = find_orphan_storage_objects(db)
        print(f"orphan_count={len(orphans)}")
        for row in orphans:
            print(f"{row.id}\t{row.backend}\t{row.source_id or '-'}\t{row.artifact_id or '-'}\t{row.object_key}")
        if args.apply and orphans:
            now = datetime.now(timezone.utc)
            for row in orphans:
                row.lifecycle_state = "orphaned"
                row.updated_at = now
            db.commit()
            print(f"marked_orphaned={len(orphans)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
