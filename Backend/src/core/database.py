import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from core.config import settings

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS weather_cache (
        cache_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_config (
        config_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nina_cache (
        cache_key  TEXT PRIMARY KEY,
        payload    TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS spotify_tokens (
        id            INTEGER PRIMARY KEY CHECK (id = 1),
        access_token  TEXT NOT NULL,
        refresh_token TEXT NOT NULL,
        expires_at    TEXT NOT NULL
    )
    """,
)


def ensure_database_directory() -> None:
    db_path = settings.sqlite_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    ensure_database_directory()
    connection = sqlite3.connect(settings.sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_db_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
