from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_diagram_foundation"
down_revision = "0005_collab_ops"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("diagrams"):
        op.create_table(
            "diagrams",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("objective", sa.Text(), nullable=True),
            sa.Column("notation", sa.String(length=32), nullable=False, server_default="bpm"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("owner", sa.String(length=128), nullable=False),
            sa.Column("collection_id", sa.String(length=64), nullable=True),
            sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("drawio_xml", sa.Text(), nullable=True),
            sa.Column("spec_json", sa.JSON(), nullable=True),
            sa.Column("source_page_ids", sa.JSON(), nullable=True),
            sa.Column("source_ids", sa.JSON(), nullable=True),
            sa.Column("actor_lanes", sa.JSON(), nullable=True),
            sa.Column("entry_points", sa.JSON(), nullable=True),
            sa.Column("exit_points", sa.JSON(), nullable=True),
            sa.Column("related_diagram_ids", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        )
        op.create_index("ix_diagrams_slug", "diagrams", ["slug"], unique=True)
        op.create_index("ix_diagrams_status", "diagrams", ["status"])
        op.create_index("ix_diagrams_collection_id", "diagrams", ["collection_id"])
        op.create_index("ix_diagrams_created_at", "diagrams", ["created_at"])
        op.create_index("ix_diagrams_updated_at", "diagrams", ["updated_at"])
        op.create_index("ix_diagrams_published_at", "diagrams", ["published_at"])

    if not _has_table("diagram_versions"):
        op.create_table(
            "diagram_versions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("diagram_id", sa.String(length=64), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("drawio_xml", sa.Text(), nullable=True),
            sa.Column("spec_json", sa.JSON(), nullable=True),
            sa.Column("change_summary", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by_agent_or_user", sa.String(length=128), nullable=False),
            sa.ForeignKeyConstraint(["diagram_id"], ["diagrams.id"]),
        )
        op.create_index("ix_diagram_versions_diagram_id", "diagram_versions", ["diagram_id"])
        op.create_index("ix_diagram_versions_created_at", "diagram_versions", ["created_at"])


def downgrade() -> None:
    if _has_table("diagram_versions"):
        op.drop_table("diagram_versions")
    if _has_table("diagrams"):
        op.drop_table("diagrams")
