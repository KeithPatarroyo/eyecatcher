"""Support: DB and path utilities. Only touch for bugs or app-wide infra."""

from .db_util import default_db_path, sqlite_connection, with_db_connection

__all__ = ["default_db_path", "sqlite_connection", "with_db_connection"]
