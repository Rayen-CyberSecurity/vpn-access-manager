"""Connection pool and the two ways of talking to PostgreSQL."""

from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from api.config import settings

# A pool rather than one connection per request: the capacity test opens two
# requests at the same instant and needs two real connections to do so.
pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=True,
)


@contextmanager
def transaction():
    """Everything inside commits together or not at all.

    The block commits on normal exit and rolls back on ANY exception,
    including the HTTPException raised by the capacity check. That is why a
    refused request can never leave a half-written row behind.
    """
    with pool.connection() as conn:
        with conn.transaction():
            yield conn


@contextmanager
def query():
    """Read-only access. No explicit transaction block needed."""
    with pool.connection() as conn:
        yield conn
