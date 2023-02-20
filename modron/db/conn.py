from __future__ import annotations

import asyncio
import functools
import inspect
import typing

import asyncpg
import asyncpg.prepared_stmt

Record = asyncpg.Record

if typing.TYPE_CHECKING:
    Prep = asyncpg.prepared_stmt.PreparedStatement[Record]
    Connection = asyncpg.Connection[Record]
    Pool = asyncpg.Pool[Record]
else:
    Prep = asyncpg.prepared_stmt.PreparedStatement
    Connection = asyncpg.Connection
    Pool = asyncpg.Pool


async def connect(url: str) -> Pool:
    pool = await asyncpg.create_pool(url, record_class=Record)
    if pool is None:
        raise RuntimeError("Could not create asyncpg connection pool")

    async with pool.acquire() as conn:
        with open("modron/db/schema.sql") as f:
            await conn.execute(f.read())

    return pool


SpecT = typing.ParamSpec("SpecT")
ReturnT = typing.TypeVar("ReturnT")
ConnT = typing.TypeVar("ConnT", bound="DBConn")
CallbackT = typing.Callable[typing.Concatenate[ConnT, Prep, SpecT], ReturnT]


class PreparedCallable(typing.Generic[ConnT, SpecT, ReturnT]):
    def __init__(
        self,
        callback: CallbackT[ConnT, SpecT, ReturnT],
        statement: str,
    ) -> None:
        self.callback = staticmethod(callback)
        self.statement = statement
        self.prepared: Prep | None = None

    def __call__(self, conn: ConnT, *args: SpecT.args, **kwargs: SpecT.kwargs) -> ReturnT:
        assert self.prepared is not None
        return self.callback(conn, self.prepared, *args, **kwargs)

    def __get__(self, instance: typing.Any, *_) -> typing.Callable[SpecT, ReturnT]:
        partial = functools.partial(self.__call__, instance)
        partial.prepare = self.prepare  # type: ignore
        return partial

    async def prepare(self, pool: Pool) -> None:
        async with pool.acquire() as conn:
            self.prepared = await conn.prepare(self.statement)


def with_prepared(
    statement: str,
) -> typing.Callable[[CallbackT[ConnT, SpecT, ReturnT]], PreparedCallable[ConnT, SpecT, ReturnT]]:
    def decorator(f: CallbackT[ConnT, SpecT, ReturnT]) -> PreparedCallable[ConnT, SpecT, ReturnT]:
        return PreparedCallable(f, statement)

    return decorator


class DBConn:
    def __init__(self, pool: Pool) -> None:
        self.pool = pool

    async def prepare(self) -> typing.Self:
        await asyncio.gather(
            *[
                partial.prepare(self.pool)
                for _, partial in inspect.getmembers(self, lambda p: isinstance(p, functools.partial))
            ]
        )
        return self
