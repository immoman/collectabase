"""add type-specific collectible columns

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _table_exists("games"):
        return

    for column_name in ["character_name", "series_name", "scale", "funko_number", "vinyl_format"]:
        if not _column_exists("games", column_name):
            op.add_column("games", sa.Column(column_name, sa.String(), nullable=True))


def downgrade() -> None:
    if not _table_exists("games"):
        return

    for column_name in ["vinyl_format", "funko_number", "scale", "series_name", "character_name"]:
        if _column_exists("games", column_name):
            op.drop_column("games", column_name)
