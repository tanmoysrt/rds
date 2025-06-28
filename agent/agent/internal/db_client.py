from __future__ import annotations

import contextlib
from typing import Literal

from MySQLdb.connections import Connection


class DatabaseClient:
    def __init__(self, db_type:Literal["mysql", "mariadb", "proxysql"], host:str, port:int|str, user:str, password:str, schema:str="", autocommit:bool=False, connect_timeout:int=5):
        if db_type not in ("mysql", "mariadb", "proxysql"):
            raise ValueError(f"Unsupported database type: {db_type}")
        self.host = host
        self.port:int = int(port) if isinstance(port, str) else port
        self.user = user
        self.password = password or ""
        self.schema = schema
        self.autocommit = autocommit
        self.connect_timeout = connect_timeout

        self._connection_instance: Connection | None = None

    @property
    def _connection(self):
        if not self._connection_instance:
            self._connection_instance = Connection(
                # In case of localhost, the client try to connect to the local socket
                host="127.0.0.1" if self.host == "localhost" else self.host,
                port=self.port,
                user=self.user,
                passwd=self.password,
                db=self.schema,
                connect_timeout=self.connect_timeout,
                autocommit=self.autocommit,
            )
        return self._connection_instance

    def close(self):
        if self._connection_instance:
            with contextlib.suppress(Exception):
                self._connection_instance.close()
            self._connection_instance = None

    def __enter__(self):
        return self

    def __del__(self):
        self.close()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def query(self, query: str, params: tuple = (), as_dict: bool = True):
        """
        Execute a single query with optional parameters.
        Args:
            query: SQL query string.
            params: Tuple of parameters for the query.
            as_dict: If True, returns results as a list of dictionaries
        Returns:
            List of rows as dictionaries (column_name: value) or
            List of lists (column names followed by rows).
        """
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall() if columns else []
                if as_dict:
                    return [dict(zip(columns, row)) for row in rows] if columns else []
                return [columns] + [list(row) for row in rows]
        except Exception as e:
            self.close()
            raise e

    def is_reachable(self) -> bool:
        """
        Check if the database is reachable.
        Returns:
            True if the database is reachable, False otherwise.
        """
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
