from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0011_ku_extraction_runs"
down_revision = "0010_claim_semantic_fields"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("knowledge_units"):
        op.create_table(
            "knowledge_units",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("source_id", sa.String(length=64), nullable=False),
            sa.Column("source_chunk_id", sa.String(length=64), nullable=True),
            sa.Column("claim_id", sa.String(length=64), nullable=True),
            sa.Column("unit_type", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("canonical_status", sa.String(length=32), nullable=False, server_default="proposed"),
            sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("topic", sa.String(length=128), nullable=True),
            sa.Column("entity_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("evidence_span_start", sa.Integer(), nullable=True),
            sa.Column("evidence_span_end", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
            sa.ForeignKeyConstraint(["source_chunk_id"], ["source_chunks.id"]),
            sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_knowledge_units_source_id", "knowledge_units", ["source_id"])
        op.create_index("ix_knowledge_units_source_chunk_id", "knowledge_units", ["source_chunk_id"])
        op.create_index("ix_knowledge_units_claim_id", "knowledge_units", ["claim_id"])
        op.create_index("ix_knowledge_units_unit_type", "knowledge_units", ["unit_type"])
        op.create_index("ix_knowledge_units_status", "knowledge_units", ["status"])
        op.create_index("ix_knowledge_units_review_status", "knowledge_units", ["review_status"])
        op.create_index("ix_knowledge_units_canonical_status", "knowledge_units", ["canonical_status"])
        op.create_index("ix_knowledge_units_created_at", "knowledge_units", ["created_at"])
        op.create_index("ix_knowledge_units_updated_at", "knowledge_units", ["updated_at"])

    if not _has_table("extraction_runs"):
        op.create_table(
            "extraction_runs",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("source_id", sa.String(length=64), nullable=False),
            sa.Column("run_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
            sa.Column("method", sa.String(length=32), nullable=False, server_default="heuristic"),
            sa.Column("task_profile", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("model_provider", sa.String(length=32), nullable=False, server_default="none"),
            sa.Column("model_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("input_chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("output_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_extraction_runs_source_id", "extraction_runs", ["source_id"])
        op.create_index("ix_extraction_runs_run_type", "extraction_runs", ["run_type"])
        op.create_index("ix_extraction_runs_status", "extraction_runs", ["status"])
        op.create_index("ix_extraction_runs_started_at", "extraction_runs", ["started_at"])
        op.create_index("ix_extraction_runs_finished_at", "extraction_runs", ["finished_at"])


def downgrade() -> None:
    if _has_table("extraction_runs"):
        op.drop_index("ix_extraction_runs_finished_at", table_name="extraction_runs")
        op.drop_index("ix_extraction_runs_started_at", table_name="extraction_runs")
        op.drop_index("ix_extraction_runs_status", table_name="extraction_runs")
        op.drop_index("ix_extraction_runs_run_type", table_name="extraction_runs")
        op.drop_index("ix_extraction_runs_source_id", table_name="extraction_runs")
        op.drop_table("extraction_runs")

    if _has_table("knowledge_units"):
        op.drop_index("ix_knowledge_units_updated_at", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_created_at", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_canonical_status", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_review_status", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_status", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_unit_type", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_claim_id", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_source_chunk_id", table_name="knowledge_units")
        op.drop_index("ix_knowledge_units_source_id", table_name="knowledge_units")
        op.drop_table("knowledge_units")
