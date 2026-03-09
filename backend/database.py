import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

# Import the new SQLAlchemy session manager
from .db.session import SessionLocal

class RowProxy:
    """Mimics sqlite3.Row – supports both dict-style and integer-style access."""
    __slots__ = ("_data", "_keys")

    def __init__(self, mapping):
        self._data = dict(mapping)
        self._keys = list(mapping.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[self._keys[key]]
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._keys

    def values(self):
        return [self._data[k] for k in self._keys]

    def items(self):
        return [(k, self._data[k]) for k in self._keys]

    def get(self, key, default=None):
        return self._data.get(key, default)


class CursorWrapper:
    """Wraps SQLAlchemy CursorResult to behave like a sqlite3 cursor."""
    def __init__(self, result):
        self.result = result
        self.lastrowid = getattr(result, "lastrowid", None)

    def fetchone(self):
        row = self.result.fetchone()
        return RowProxy(row._mapping) if row else None

    def fetchall(self):
        rows = self.result.fetchall()
        return [RowProxy(row._mapping) for row in rows]

class LegacyDBWrapper:
    """
    A temporary wrapper to make a SQLAlchemy Session behave like a raw sqlite3 connection.
    """
    def __init__(self, session):
        self.session = session
        self.conn = session.connection()

    def execute(self, statement: str, parameters=None):
        if parameters is None:
            parameters = ()
        # exec_driver_sql passes raw SQL containing "?" directly to sqlite3
        result = self.conn.exec_driver_sql(statement, parameters)
        return CursorWrapper(result)

    def commit(self):
        self.session.commit()
        
    def rollback(self):
        self.session.rollback()

@contextmanager
def get_db():
    db = SessionLocal()
    wrapper = LegacyDBWrapper(db)
    try:
        yield wrapper
    finally:
        db.close()

def dict_from_row(row) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    if isinstance(row, RowProxy):
        return dict(row.items())
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)

def get_app_meta(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_db() as db:
        row = db.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

def get_app_meta_many(keys: list[str]) -> Dict[str, str]:
    if not keys:
        return {}
    placeholders = ",".join(["?"] * len(keys))
    with get_db() as db:
        cursor = db.execute(
            f"SELECT key, value FROM app_meta WHERE key IN ({placeholders})", tuple(keys)
        )
        return {row["key"]: row["value"] for row in cursor.fetchall()}

def set_app_meta(key: str, value: str):
    with get_db() as db:
        db.execute(
            """
            INSERT INTO app_meta (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        db.commit()

# Database initialization logic is now handled by Alembic schema migrations.
def init_db():
    pass
