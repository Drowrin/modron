from __future__ import annotations

import typing

import asyncpg


class DBConn:
    @classmethod
    async def connect(cls, url: str) -> DBConn:
        conn = await asyncpg.connect(url)

        # TODO: remove
        await conn.execute("DROP TABLE Players;" "DROP TABLE Characters;" "DROP TABLE Games; DROP TYPE game_status;")

        with open("modron/db/schema.sql") as f:
            await conn.execute(f.read())

        return cls(conn)

    def __init__(self, conn: asyncpg.Connection[asyncpg.Record]) -> None:
        self.conn = conn

    async def close(self) -> None:
        await self.conn.close()

    async def insert_game(self, *, name: str, description: str, system: str, guild_id: int, owner_id: int) -> int:
        game_id = await self.conn.fetchval(
            "INSERT INTO Games (name, description, system, guild_id, owner_id)"
            "VALUES ($1, $2, $3, $4, $5)"
            "RETURNING id;",
            name,
            description,
            system,
            guild_id,
            owner_id,
        )

        assert isinstance(game_id, int)

        return game_id

    async def insert_character(
        self,
        *,
        game_id: int,
        author_id: int,
        name: str,
        brief: str,
        description: str,
        pronouns: str | None = None,
        image: str | None = None,
    ) -> int:
        character_id = await self.conn.fetchval(
            "INSERT INTO Characters (game_id, author_id, name, pronouns, image, brief, description)"
            "VALUES ($1, $2, $3, $4, $5, $6, $7)"
            "RETURNING id;",
            game_id,
            author_id,
            name,
            pronouns,
            image,
            brief,
            description,
        )

        assert isinstance(character_id, int)

        return character_id

    async def insert_player(self, *, user_id: int, game_id: int, role: str, character_id: int | None = None) -> None:
        await self.conn.execute(
            "INSERT INTO Players (user_id, game_id, character_id, role)" "VALUES ($1, $2, $3, $4);",
            user_id,
            game_id,
            character_id,
            role,
        )

    async def fetchval(self, query: str, *args: object) -> typing.Any:
        return await self.conn.fetchval(query, *args)

    async def fetchrow(self, query: str, *args: object) -> asyncpg.Record | None:
        return await self.conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args: object) -> list[asyncpg.Record]:
        return await self.conn.fetch(query, *args)
