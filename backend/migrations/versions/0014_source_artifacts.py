from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0014_source_artifacts"
down_revision = "0013_collection_memberships"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("source_artifacts"):
        return

    op.create_table(
        "source_artifacts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="available"),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_artifacts_source_id", "source_artifacts", ["source_id"])
    op.create_index("ix_source_artifacts_artifact_type", "source_artifacts", ["artifact_type"])
    op.create_index("ix_source_artifacts_created_at", "source_artifacts", ["created_at"])


def downgrade() -> None:
    if not _has_table("source_artifacts"):
        return

    op.drop_index("ix_source_artifacts_created_at", table_name="source_artifacts")
    op.drop_index("ix_source_artifacts_artifact_type", table_name="source_artifacts")
    op.drop_index("ix_source_artifacts_source_id", table_name="source_artifacts")
    op.drop_table("source_artifacts")
