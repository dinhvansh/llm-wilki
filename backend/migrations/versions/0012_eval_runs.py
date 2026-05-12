from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0012_eval_runs"
down_revision = "0011_ku_extraction_runs"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("eval_runs"):
        return

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_type", sa.String(length=32), nullable=False),
        sa.Column("run_name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("case_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quality_gates_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("tags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("report_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.String(length=128), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eval_runs_run_type", "eval_runs", ["run_type"])
    op.create_index("ix_eval_runs_status", "eval_runs", ["status"])
    op.create_index("ix_eval_runs_success", "eval_runs", ["success"])
    op.create_index("ix_eval_runs_created_at", "eval_runs", ["created_at"])


def downgrade() -> None:
    if not _has_table("eval_runs"):
        return
    op.drop_index("ix_eval_runs_created_at", table_name="eval_runs")
    op.drop_index("ix_eval_runs_success", table_name="eval_runs")
    op.drop_index("ix_eval_runs_status", table_name="eval_runs")
    op.drop_index("ix_eval_runs_run_type", table_name="eval_runs")
    op.drop_table("eval_runs")
