import os
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from sqlalchemy.exc import OperationalError

# Import the new SQLAlchemy session manager
from .db.session import SessionLocal

_INIT_LOCK = Lock()
_INIT_DONE = False
DEFAULT_PLATFORMS = [
    ("PlayStation 5", "Sony", "Console"),
    ("PlayStation 4", "Sony", "Console"),
    ("PlayStation 3", "Sony", "Console"),
    ("PlayStation 2", "Sony", "Console"),
    ("PlayStation", "Sony", "Console"),
    ("PSP", "Sony", "Handheld"),
    ("PS Vita", "Sony", "Handheld"),
    ("Xbox Series X/S", "Microsoft", "Console"),
    ("Xbox One", "Microsoft", "Console"),
    ("Xbox 360", "Microsoft", "Console"),
    ("Xbox", "Microsoft", "Console"),
    ("Nintendo Switch 2", "Nintendo", "Console"),
    ("Nintendo Switch", "Nintendo", "Console"),
    ("Wii U", "Nintendo", "Console"),
    ("Wii", "Nintendo", "Console"),
    ("GameCube", "Nintendo", "Console"),
    ("Nintendo 64", "Nintendo", "Console"),
    ("SNES", "Nintendo", "Console"),
    ("NES", "Nintendo", "Console"),
    ("Game Boy Advance", "Nintendo", "Handheld"),
    ("Game Boy Color", "Nintendo", "Handheld"),
    ("Game Boy", "Nintendo", "Handheld"),
    ("Nintendo 3DS", "Nintendo", "Handheld"),
    ("Nintendo DS", "Nintendo", "Handheld"),
    ("PC", "Various", "Platform"),
    ("Sega Dreamcast", "Sega", "Console"),
    ("Sega Saturn", "Sega", "Console"),
    ("Sega Genesis/Mega Drive", "Sega", "Console"),
    ("Sega Master System", "Sega", "Console"),
    ("Sega Game Gear", "Sega", "Handheld"),
]

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
    try:
        with get_db() as db:
            row = db.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
    except OperationalError as exc:
        if "no such table: app_meta" in str(exc).lower():
            return default
        raise

def get_app_meta_many(keys: list[str]) -> Dict[str, str]:
    if not keys:
        return {}
    placeholders = ",".join(["?"] * len(keys))
    try:
        with get_db() as db:
            cursor = db.execute(
                f"SELECT key, value FROM app_meta WHERE key IN ({placeholders})", tuple(keys)
            )
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    except OperationalError as exc:
        if "no such table: app_meta" in str(exc).lower():
            return {}
        raise

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

def init_db():
    global _INIT_DONE
    if _INIT_DONE:
        return

    with _INIT_LOCK:
        if _INIT_DONE:
            return

        from alembic import command
        from alembic.config import Config
        from .db.session import get_database_url

        database_url = get_database_url()
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "", 1)
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        alembic_ini = Path(__file__).resolve().parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("script_location", str((alembic_ini.parent / "alembic").resolve()))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        with get_db() as db:
            row = db.execute("SELECT COUNT(*) AS count FROM platforms").fetchone()
            platform_count = int(row["count"]) if row else 0
            if platform_count == 0:
                for name, manufacturer, platform_type in DEFAULT_PLATFORMS:
                    db.execute(
                        "INSERT OR IGNORE INTO platforms (name, manufacturer, type) VALUES (?, ?, ?)",
                        (name, manufacturer, platform_type),
                    )
                db.commit()
        _INIT_DONE = True
