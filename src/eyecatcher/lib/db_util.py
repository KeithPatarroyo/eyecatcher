"""
Shared SQLite connection helper for route modules that use a database.
"""

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager


def default_db_path(filename: str) -> str:
    """
    Return the default path for a database file under the project data/ directory.

    Args:
        filename: Database filename (e.g. "community.db", "genealogy.db").

    Returns:
        Absolute path: get_root_dir() / "data" / filename.
    """
    from .. import get_root_dir

    return os.path.join(get_root_dir(), "data", filename)


def sqlite_connection(
    path: str,
    pragmas: tuple[str, ...] = (),
) -> sqlite3.Connection:
    """
    Open a SQLite connection with row_factory and optional pragmas.

    Creates the parent directory of path if needed. Sets row_factory to
    sqlite3.Row so rows are dict-like.

    Args:
        path: Database file path.
        pragmas: Optional sequence of SQL statements to run after connect
                 (e.g. ("PRAGMA foreign_keys = ON",)).

    Returns:
        Open connection (caller must close it).
    """
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    for stmt in pragmas:
        conn.execute(stmt)
    return conn


@contextmanager
def with_db_connection(
    path: str,
    pragmas: tuple[str, ...] = (),
) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager: yield a connection and close it on exit.

    Use in route handlers so connection is always closed. Catch Exception
    in the route and return api_error(str(e), 500) if needed.
    """
    conn = sqlite_connection(path, pragmas)
    try:
        yield conn
    finally:
        conn.close()
