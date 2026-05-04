from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from app.services.auth import DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD, hash_password


revision = "0003_auth_governance"
down_revision = "0002_runtime_schema_cols"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("ix_users_role", "users", ["role"])

    if not _has_table("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
        op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    bind = op.get_bind()
    existing = bind.execute(sa.text("select id from users where email = :email"), {"email": DEV_ADMIN_EMAIL}).first()
    if not existing:
        now = datetime.now(timezone.utc)
        bind.execute(
            sa.text(
                """
                insert into users (id, email, name, role, password_hash, is_active, created_at, updated_at)
                values (:id, :email, :name, :role, :password_hash, true, :created_at, :updated_at)
                """
            ),
            {
                "id": "user-dev-admin",
                "email": DEV_ADMIN_EMAIL,
                "name": "Dev Admin",
                "role": "admin",
                "password_hash": hash_password(DEV_ADMIN_PASSWORD),
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    if _has_table("auth_sessions"):
        op.drop_table("auth_sessions")
    if _has_table("users"):
        op.drop_table("users")

