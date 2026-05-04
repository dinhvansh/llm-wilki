from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0010_claim_semantic_fields"
down_revision = "0009_runtime_ai_task_profiles"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    if not _has_table("claims"):
        return
    if not _has_column("claims", "extraction_method"):
        op.add_column("claims", sa.Column("extraction_method", sa.String(length=32), nullable=False, server_default="heuristic"))
    if not _has_column("claims", "evidence_span_start"):
        op.add_column("claims", sa.Column("evidence_span_start", sa.Integer(), nullable=True))
    if not _has_column("claims", "evidence_span_end"):
        op.add_column("claims", sa.Column("evidence_span_end", sa.Integer(), nullable=True))
    if not _has_column("claims", "metadata_json"):
        op.add_column("claims", sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    if not _has_table("claims"):
        return
    if _has_column("claims", "metadata_json"):
        op.drop_column("claims", "metadata_json")
    if _has_column("claims", "evidence_span_end"):
        op.drop_column("claims", "evidence_span_end")
    if _has_column("claims", "evidence_span_start"):
        op.drop_column("claims", "evidence_span_start")
    if _has_column("claims", "extraction_method"):
        op.drop_column("claims", "extraction_method")
