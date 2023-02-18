from __future__ import annotations

import asyncpg


async def connect(url: str) -> asyncpg.Connection[asyncpg.Record]:
    conn = await asyncpg.connect(url)

    await conn.execute(
        "DROP TABLE IF EXISTS Players;"
        "DROP TABLE IF EXISTS Characters;"
        "DROP TABLE IF EXISTS Games;"
        "DROP TYPE IF EXISTS game_status;"
    )

    with open("modron/db/schema.sql") as f:
        await conn.execute(f.read())

    return conn


class DBConn:
    def __init__(self, conn: asyncpg.Connection[asyncpg.Record]) -> None:
        self.conn = conn
