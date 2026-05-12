from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0013_collection_memberships"
down_revision = "0012_eval_runs"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("collection_memberships"):
        return

    op.create_table(
        "collection_memberships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_memberships_collection_id", "collection_memberships", ["collection_id"])
    op.create_index("ix_collection_memberships_user_id", "collection_memberships", ["user_id"])
    op.create_index("ix_collection_memberships_role", "collection_memberships", ["role"])


def downgrade() -> None:
    if not _has_table("collection_memberships"):
        return

    op.drop_index("ix_collection_memberships_role", table_name="collection_memberships")
    op.drop_index("ix_collection_memberships_user_id", table_name="collection_memberships")
    op.drop_index("ix_collection_memberships_collection_id", table_name="collection_memberships")
    op.drop_table("collection_memberships")
