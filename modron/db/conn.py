from __future__ import annotations

import asyncpg


async def connect(url: str) -> asyncpg.Connection[asyncpg.Record]:
    conn = await asyncpg.connect(url)

    with open("modron/db/schema.sql") as f:
        await conn.execute(f.read())

    return conn


class DBConn:
    def __init__(self, conn: asyncpg.Connection[asyncpg.Record]) -> None:
        self.conn = conn
