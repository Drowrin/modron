from __future__ import annotations

import functools
import typing

import asyncpg
import asyncpg.pool

Record = asyncpg.Record

if typing.TYPE_CHECKING:
    Conn = asyncpg.pool.PoolConnectionProxy[Record]
    Pool = asyncpg.Pool[Record]
else:
    Conn = asyncpg.pool.PoolConnectionProxy
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
_T = typing.TypeVar("_T", bound="DBConn")
CallbackT = typing.Callable[typing.Concatenate[_T, Conn, SpecT], typing.Coroutine[typing.Any, typing.Any, ReturnT]]
TransformedCallbackT = typing.Callable[typing.Concatenate[_T, SpecT], typing.Coroutine[typing.Any, typing.Any, ReturnT]]


def with_conn(f: CallbackT[_T, SpecT, ReturnT]) -> TransformedCallbackT[_T, SpecT, ReturnT]:
    @functools.wraps(f)
    async def inner(self: _T, *args: SpecT.args, **kwargs: SpecT.kwargs) -> ReturnT:
        async with self.pool.acquire() as conn:
            return await f(self, conn, *args, **kwargs)

    return inner


class DBConn:
    def __init__(self, pool: Pool) -> None:
        self.pool = pool
