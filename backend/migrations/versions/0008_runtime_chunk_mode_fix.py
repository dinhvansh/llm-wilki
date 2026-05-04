from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_runtime_chunk_mode_fix"
down_revision = "0007_runtime_chunk_mode"
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
    if _has_table("runtime_config") and not _has_column("runtime_config", "chunk_mode"):
        op.add_column(
            "runtime_config",
            sa.Column("chunk_mode", sa.String(length=32), nullable=False, server_default="structured"),
        )
        op.execute("UPDATE runtime_config SET chunk_mode = 'structured' WHERE chunk_mode IS NULL OR chunk_mode = ''")


def downgrade() -> None:
    if _has_table("runtime_config") and _has_column("runtime_config", "chunk_mode"):
        op.drop_column("runtime_config", "chunk_mode")
