from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0017_notes"
down_revision = "0016_storage_objects"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("notes"):
        op.create_table(
            "notes",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("scope", sa.String(length=32), nullable=False, server_default="private"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("owner_id", sa.String(length=64), nullable=True),
            sa.Column("owner_name", sa.String(length=128), nullable=False, server_default="Current User"),
            sa.Column("collection_id", sa.String(length=64), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["archived_at", "collection_id", "created_at", "owner_id", "owner_name", "scope", "status", "updated_at"]:
            op.create_index(f"ix_notes_{column}", "notes", [column])

    if not _has_table("note_anchors"):
        op.create_table(
            "note_anchors",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("note_id", sa.String(length=64), nullable=False),
            sa.Column("target_type", sa.String(length=64), nullable=False),
            sa.Column("target_id", sa.String(length=128), nullable=True),
            sa.Column("source_id", sa.String(length=64), nullable=True),
            sa.Column("chunk_id", sa.String(length=64), nullable=True),
            sa.Column("artifact_id", sa.String(length=64), nullable=True),
            sa.Column("page_id", sa.String(length=64), nullable=True),
            sa.Column("section_key", sa.String(length=128), nullable=True),
            sa.Column("review_item_id", sa.String(length=64), nullable=True),
            sa.Column("ask_message_id", sa.String(length=64), nullable=True),
            sa.Column("citation_id", sa.String(length=128), nullable=True),
            sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
            sa.ForeignKeyConstraint(["ask_message_id"], ["chat_messages.id"]),
            sa.ForeignKeyConstraint(["chunk_id"], ["source_chunks.id"]),
            sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
            sa.ForeignKeyConstraint(["page_id"], ["pages.id"]),
            sa.ForeignKeyConstraint(["review_item_id"], ["review_items.id"]),
            sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["artifact_id", "ask_message_id", "chunk_id", "citation_id", "created_at", "note_id", "page_id", "review_item_id", "section_key", "source_id", "target_id", "target_type"]:
            op.create_index(f"ix_note_anchors_{column}", "note_anchors", [column])

    if not _has_table("note_versions"):
        op.create_table(
            "note_versions",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("note_id", sa.String(length=64), nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("change_summary", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_note_versions_created_at", "note_versions", ["created_at"])
        op.create_index("ix_note_versions_note_id", "note_versions", ["note_id"])


def downgrade() -> None:
    if _has_table("note_versions"):
        op.drop_index("ix_note_versions_note_id", table_name="note_versions")
        op.drop_index("ix_note_versions_created_at", table_name="note_versions")
        op.drop_table("note_versions")
    if _has_table("note_anchors"):
        for column in ["target_type", "target_id", "source_id", "section_key", "review_item_id", "page_id", "note_id", "created_at", "citation_id", "chunk_id", "ask_message_id", "artifact_id"]:
            op.drop_index(f"ix_note_anchors_{column}", table_name="note_anchors")
        op.drop_table("note_anchors")
    if _has_table("notes"):
        for column in ["updated_at", "status", "scope", "owner_name", "owner_id", "created_at", "collection_id", "archived_at"]:
            op.drop_index(f"ix_notes_{column}", table_name="notes")
        op.drop_table("notes")
