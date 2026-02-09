"""
Shared SQLite connection helper for route modules that use a database.
"""

import os
import sqlite3


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
