"""add price_catalog indexes

Revision ID: a1b2c3d4e5f6
Revises: 7b5a4fab11fd
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7b5a4fab11fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=:name"),
        {"name": name},
    )
    return result.scalar() > 0


def upgrade() -> None:
    if not _table_exists("price_catalog"):
        return

    for index_name, columns in [
        ("idx_price_catalog_platform", ["platform"]),
        ("idx_price_catalog_title", ["title"]),
        ("idx_price_catalog_platform_title", ["platform", "title"]),
    ]:
        if not _index_exists(index_name):
            op.create_index(index_name, "price_catalog", columns)


def downgrade() -> None:
    if not _table_exists("price_catalog"):
        return

    for index_name in [
        "idx_price_catalog_platform_title",
        "idx_price_catalog_title",
        "idx_price_catalog_platform",
    ]:
        if _index_exists(index_name):
            op.drop_index(index_name, table_name="price_catalog")
