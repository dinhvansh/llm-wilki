from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0016_storage_objects"
down_revision = "0015_departments"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("storage_objects"):
        return

    op.create_table(
        "storage_objects",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("local_path", sa.String(length=1024), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("owner", sa.String(length=128), nullable=False, server_default="system"),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("artifact_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_storage_objects_artifact_id", "storage_objects", ["artifact_id"])
    op.create_index("ix_storage_objects_backend", "storage_objects", ["backend"])
    op.create_index("ix_storage_objects_bucket", "storage_objects", ["bucket"])
    op.create_index("ix_storage_objects_checksum_sha256", "storage_objects", ["checksum_sha256"])
    op.create_index("ix_storage_objects_created_at", "storage_objects", ["created_at"])
    op.create_index("ix_storage_objects_lifecycle_state", "storage_objects", ["lifecycle_state"])
    op.create_index("ix_storage_objects_object_key", "storage_objects", ["object_key"])
    op.create_index("ix_storage_objects_owner", "storage_objects", ["owner"])
    op.create_index("ix_storage_objects_source_id", "storage_objects", ["source_id"])
    op.create_index("ix_storage_objects_updated_at", "storage_objects", ["updated_at"])


def downgrade() -> None:
    if not _has_table("storage_objects"):
        return
    op.drop_index("ix_storage_objects_updated_at", table_name="storage_objects")
    op.drop_index("ix_storage_objects_source_id", table_name="storage_objects")
    op.drop_index("ix_storage_objects_owner", table_name="storage_objects")
    op.drop_index("ix_storage_objects_object_key", table_name="storage_objects")
    op.drop_index("ix_storage_objects_lifecycle_state", table_name="storage_objects")
    op.drop_index("ix_storage_objects_created_at", table_name="storage_objects")
    op.drop_index("ix_storage_objects_checksum_sha256", table_name="storage_objects")
    op.drop_index("ix_storage_objects_bucket", table_name="storage_objects")
    op.drop_index("ix_storage_objects_backend", table_name="storage_objects")
    op.drop_index("ix_storage_objects_artifact_id", table_name="storage_objects")
    op.drop_table("storage_objects")
