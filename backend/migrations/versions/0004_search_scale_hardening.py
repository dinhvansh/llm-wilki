from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_search_scale"
down_revision = "0003_auth_governance"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    _add_column_if_missing("runtime_config", sa.Column("search_result_limit", sa.Integer(), nullable=False, server_default=sa.text("20")))
    _add_column_if_missing("runtime_config", sa.Column("graph_node_limit", sa.Integer(), nullable=False, server_default=sa.text("250")))
    _add_column_if_missing("runtime_config", sa.Column("lint_page_limit", sa.Integer(), nullable=False, server_default=sa.text("500")))

    for table_name, columns in {
        "sources": ["parse_status", "collection_id", "uploaded_at"],
        "pages": ["status", "page_type", "collection_id", "published_at"],
        "source_chunks": ["source_id", "chunk_index"],
        "claims": ["source_chunk_id", "review_status", "canonical_status"],
        "page_claim_links": ["page_id", "claim_id"],
        "page_source_links": ["page_id", "source_id"],
        "audit_logs": ["object_type", "object_id", "created_at"],
        "jobs": ["status", "job_type", "started_at", "input_ref"],
    }.items():
        for column_name in columns:
            if _has_column(table_name, column_name):
                _create_index_if_missing(f"ix_{table_name}_{column_name}_phase16", table_name, [column_name])


def downgrade() -> None:
    pass

