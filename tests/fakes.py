"""Test doubles for SQLAlchemy's async session.

The codebase issues raw ``text()`` SQL almost everywhere, so unit tests stub
results by matching on a distinctive substring of the SQL. This keeps the
tests readable and order-independent, at the cost of not exercising the SQL
itself — that is what the PostGIS integration suite in docs/ROADMAP.md P3 is
for. See the "已知缺口" section of TESTING.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class Row:
    """Mimics a SQLAlchemy ``Row``: attribute access plus ``._mapping``."""

    def __init__(self, **fields: Any) -> None:
        self.__dict__.update(fields)

    @property
    def _mapping(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    def __getitem__(self, index: int) -> Any:
        return list(self._mapping.values())[index]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Row({self._mapping})"


class FakeScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None


class FakeResult:
    def __init__(self, rows: Iterable[Any] = (), rowcount: int | None = None) -> None:
        self._rows = list(rows)
        self.rowcount = len(self._rows) if rowcount is None else rowcount

    def fetchone(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any | None:
        return self.fetchone()

    def all(self) -> list[Any]:
        return self.fetchall()

    def scalar_one_or_none(self) -> Any | None:
        if not self._rows:
            return None
        if len(self._rows) > 1:
            raise AssertionError("scalar_one_or_none() got multiple rows")
        return self._rows[0]

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._rows)

    def __iter__(self):
        return iter(self._rows)


class _Rule:
    def __init__(self, match: str, result: Any, limit: int | None) -> None:
        self.match = match
        self.result = result
        self.limit = limit
        self.hits = 0


class FakeSession:
    """Stands in for ``AsyncSession`` in unit tests.

    Only the surface the application actually uses is implemented:
    ``execute``, ``commit``, ``rollback``, ``add``, ``delete``, ``refresh``
    and ``begin_nested``.
    """

    def __init__(self) -> None:
        self._rules: list[_Rule] = []
        self.executed: list[tuple[str, dict[str, Any] | None]] = []
        self.commits = 0
        self.rollbacks = 0
        self.added: list[Any] = []
        self.deleted: list[Any] = []

    # ---- stubbing API -------------------------------------------------

    def when(
        self,
        match: str,
        rows: Iterable[Any] = (),
        *,
        rowcount: int | None = None,
        times: int | None = None,
    ) -> FakeSession:
        """Return ``rows`` for the next query whose SQL contains ``match``.

        Rules are matched in insertion order; ``times`` limits how often a
        rule may fire, which lets a test stub the same query differently on
        successive calls.
        """
        self._rules.append(_Rule(match, FakeResult(rows, rowcount), times))
        return self

    def when_raises(self, match: str, exc: BaseException) -> FakeSession:
        self._rules.append(_Rule(match, exc, None))
        return self

    def sql_matching(self, match: str) -> list[str]:
        return [sql for sql, _ in self.executed if match in sql]

    def params_for(self, match: str) -> list[dict[str, Any] | None]:
        return [params for sql, params in self.executed if match in sql]

    # ---- AsyncSession surface -----------------------------------------

    async def execute(self, statement: Any, params: Any = None) -> FakeResult:
        sql = " ".join(str(statement).split())
        self.executed.append((sql, params))

        for rule in self._rules:
            if rule.match not in sql:
                continue
            if rule.limit is not None and rule.hits >= rule.limit:
                continue
            rule.hits += 1
            if isinstance(rule.result, BaseException):
                raise rule.result
            return rule.result

        return FakeResult([])

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, obj: Any) -> None:
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    def begin_nested(self) -> _FakeNested:
        return _FakeNested()


class _FakeNested:
    async def __aenter__(self) -> _FakeNested:
        return self

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False
