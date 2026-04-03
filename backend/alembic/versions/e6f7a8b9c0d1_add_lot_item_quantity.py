"""add quantity to lot items

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-04-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if _table_exists("lot_items") and not _column_exists("lot_items", "quantity"):
        op.add_column(
            "lot_items",
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        )
        op.execute("UPDATE lot_items SET quantity = 1 WHERE quantity IS NULL OR quantity < 1")


def downgrade() -> None:
    if _table_exists("lot_items") and _column_exists("lot_items", "quantity"):
        op.drop_column("lot_items", "quantity")
