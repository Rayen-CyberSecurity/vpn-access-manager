"""Database connection helpers."""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from api.config import settings


@contextmanager
def query():
    """Open a database connection for read operations."""
    with psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
    ) as conn:
        yield conn


@contextmanager
def transaction():
    """Open a database connection for write operations."""
    with psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
    ) as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
