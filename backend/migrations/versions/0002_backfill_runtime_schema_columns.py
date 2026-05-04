from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0002_runtime_schema_cols"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing("sources", sa.Column("collection_id", sa.String(length=64), nullable=True))
    _add_column_if_missing("pages", sa.Column("collection_id", sa.String(length=64), nullable=True))
    _add_column_if_missing("source_chunks", sa.Column("metadata_json", sa.JSON(), nullable=True))

    _add_column_if_missing("jobs", sa.Column("steps_json", sa.JSON(), nullable=True))
    _add_column_if_missing(
        "jobs",
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    _add_column_if_missing(
        "jobs",
        sa.Column("actor", sa.String(length=128), nullable=False, server_default=sa.text("'System'")),
    )
    _add_column_if_missing("jobs", sa.Column("retry_of_job_id", sa.String(length=64), nullable=True))
    _add_column_if_missing(
        "jobs",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    _add_column_if_missing(
        "jobs",
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
    )
    _add_column_if_missing("jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing(
        "jobs",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    # This migration intentionally has no destructive downgrade because it
    # backfills columns that may predate Alembic in existing installations.
    pass
