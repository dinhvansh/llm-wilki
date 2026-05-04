from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_collab_ops"
down_revision = "0004_search_scale"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("review_comments"):
        op.create_table(
            "review_comments",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("review_item_id", sa.String(length=64), nullable=False),
            sa.Column("actor", sa.String(length=128), nullable=False),
            sa.Column("comment", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_review_comments_review_item_id", "review_comments", ["review_item_id"])
        op.create_index("ix_review_comments_created_at", "review_comments", ["created_at"])

    if not _has_table("saved_views"):
        op.create_table(
            "saved_views",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("owner", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("view_type", sa.String(length=64), nullable=False),
            sa.Column("filters_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_saved_views_owner", "saved_views", ["owner"])
        op.create_index("ix_saved_views_view_type", "saved_views", ["view_type"])
        op.create_index("ix_saved_views_updated_at", "saved_views", ["updated_at"])


def downgrade() -> None:
    if _has_table("saved_views"):
        op.drop_table("saved_views")
    if _has_table("review_comments"):
        op.drop_table("review_comments")

