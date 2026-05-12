from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0015_departments"
down_revision = "0014_source_artifacts"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_table("departments"):
        op.create_table(
            "departments",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_departments_name", "departments", ["name"], unique=True)
        op.create_index("ix_departments_slug", "departments", ["slug"], unique=True)

    if not _has_column("users", "department_id"):
        op.add_column("users", sa.Column("department_id", sa.String(length=64), nullable=True))
        op.create_foreign_key("fk_users_department_id_departments", "users", "departments", ["department_id"], ["id"])
        op.create_index("ix_users_department_id", "users", ["department_id"])


def downgrade() -> None:
    if _has_column("users", "department_id"):
        op.drop_index("ix_users_department_id", table_name="users")
        op.drop_constraint("fk_users_department_id_departments", "users", type_="foreignkey")
        op.drop_column("users", "department_id")

    if _has_table("departments"):
        op.drop_index("ix_departments_slug", table_name="departments")
        op.drop_index("ix_departments_name", table_name="departments")
        op.drop_table("departments")
