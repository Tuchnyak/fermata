import sqlite3
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

type Params = Sequence[Any] | Mapping[str, Any]


class Db:
    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection

    @classmethod
    def open(cls, path: str | Path) -> "Db":
        conn = sqlite3.connect(path, autocommit=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return cls(conn)

    def query[T](
        self, sql: str, params: Params = (), *, mapper: Callable[[sqlite3.Row], T]
    ) -> list[T]:
        return [mapper(row) for row in self._conn.execute(sql, params).fetchall()]

    def query_one[T](
        self, sql: str, params: Params = (), *, mapper: Callable[[sqlite3.Row], T]
    ) -> T | None:
        row = self._conn.execute(sql, params).fetchone()
        return None if row is None else mapper(row)

    def execute(self, sql: str, params: Params = ()) -> int:
        return self._conn.execute(sql, params).rowcount

    def insert(self, sql: str, params: Params = ()) -> int | None:
        return self._conn.execute(sql, params).lastrowid

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._conn.in_transaction:
            raise RuntimeError("Nested transactions are not supported")
        self._conn.execute("BEGIN")
        try:
            yield
            self._conn.execute("COMMIT")
        except BaseException:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
            raise
