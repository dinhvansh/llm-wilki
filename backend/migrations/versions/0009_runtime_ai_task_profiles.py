from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "0009_runtime_ai_task_profiles"
down_revision = "0008_runtime_chunk_mode_fix"
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
    if _has_table("runtime_config") and not _has_column("runtime_config", "ai_task_profiles"):
        op.add_column(
            "runtime_config",
            sa.Column("ai_task_profiles", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
        rows = op.get_bind().execute(
            sa.text(
                """
                SELECT id, answer_provider, answer_model, answer_api_key, answer_base_url, answer_timeout_seconds,
                       ingest_provider, ingest_model, ingest_api_key, ingest_base_url, ingest_timeout_seconds,
                       embedding_provider, embedding_model, embedding_api_key, embedding_base_url
                FROM runtime_config
                """
            )
        ).mappings()
        for row in rows:
            task_profiles = {
                "ingest_summary": {
                    "provider": row["ingest_provider"] or "none",
                    "model": row["ingest_model"] or "",
                    "apiKey": row["ingest_api_key"] or "",
                    "baseUrl": row["ingest_base_url"] or "",
                    "timeoutSeconds": row["ingest_timeout_seconds"] or 90,
                },
                "claim_extraction": {
                    "provider": row["ingest_provider"] or "none",
                    "model": row["ingest_model"] or "",
                    "apiKey": row["ingest_api_key"] or "",
                    "baseUrl": row["ingest_base_url"] or "",
                    "timeoutSeconds": row["ingest_timeout_seconds"] or 90,
                },
                "entity_glossary_timeline": {
                    "provider": row["ingest_provider"] or "none",
                    "model": row["ingest_model"] or "",
                    "apiKey": row["ingest_api_key"] or "",
                    "baseUrl": row["ingest_base_url"] or "",
                    "timeoutSeconds": row["ingest_timeout_seconds"] or 90,
                },
                "bpm_generation": {
                    "provider": row["ingest_provider"] or "none",
                    "model": row["ingest_model"] or "",
                    "apiKey": row["ingest_api_key"] or "",
                    "baseUrl": row["ingest_base_url"] or "",
                    "timeoutSeconds": row["ingest_timeout_seconds"] or 90,
                },
                "ask_answer": {
                    "provider": row["answer_provider"] or "none",
                    "model": row["answer_model"] or "",
                    "apiKey": row["answer_api_key"] or "",
                    "baseUrl": row["answer_base_url"] or "",
                    "timeoutSeconds": row["answer_timeout_seconds"] or 90,
                },
                "review_assist": {
                    "provider": row["answer_provider"] or "none",
                    "model": row["answer_model"] or "",
                    "apiKey": row["answer_api_key"] or "",
                    "baseUrl": row["answer_base_url"] or "",
                    "timeoutSeconds": row["answer_timeout_seconds"] or 90,
                },
                "embeddings": {
                    "provider": row["embedding_provider"] or "none",
                    "model": row["embedding_model"] or "",
                    "apiKey": row["embedding_api_key"] or "",
                    "baseUrl": row["embedding_base_url"] or "",
                    "timeoutSeconds": 90,
                },
            }
            op.get_bind().execute(
                sa.text("UPDATE runtime_config SET ai_task_profiles = :profiles WHERE id = :id"),
                {"profiles": json.dumps(task_profiles), "id": row["id"]},
            )


def downgrade() -> None:
    if _has_table("runtime_config") and _has_column("runtime_config", "ai_task_profiles"):
        op.drop_column("runtime_config", "ai_task_profiles")
