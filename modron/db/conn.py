from __future__ import annotations

import typing

import asyncpg

from modron.db.models import Game
from modron.exceptions import GameNotFoundError


class ModronRecord(asyncpg.Record):
    def __getattr__(self, name: str) -> typing.Any:
        return self[name]


class DBConn:
    @classmethod
    async def connect(cls, url: str) -> DBConn:
        conn = await asyncpg.connect(url, record_class=ModronRecord)

        with open("modron/db/schema.sql") as f:
            await conn.execute(f.read())

        return cls(conn)

    def __init__(self, conn: asyncpg.Connection[ModronRecord]) -> None:
        self.conn = conn

    async def close(self) -> None:
        await self.conn.close()

    async def insert_game(
        self,
        *,
        name: str,
        description: str,
        system: str,
        guild_id: int,
        owner_id: int,
        image: str | None = None,
        thumb: str | None = None,
    ) -> Game:
        row = await self.conn.fetchrow(
            "INSERT INTO Games (name, description, system, guild_id, owner_id, image, thumb)"
            "VALUES ($1, $2, $3, $4, $5, $6, $7)"
            "RETURNING *;",
            name,
            description,
            system,
            guild_id,
            owner_id,
            image,
            thumb,
        )

        assert row is not None

        return Game(**dict(row))

    async def get_game(self, game_id: int, guild_id: int) -> Game:
        record = await self.conn.fetchrow(
            """
            SELECT *
            FROM Games
            WHERE game_id = $1 AND guild_id = $2;
            """,
            game_id,
            guild_id,
        )

        if record is None:
            raise GameNotFoundError(game_id)

        return Game(**dict(record))

    async def get_owned_game(self, game_id: int, owner_id: int) -> Game:
        record = await self.conn.fetchrow(
            """
            SELECT *
            FROM Games
            WHERE game_id = $1 AND owner_id = $2;
            """,
            game_id,
            owner_id,
        )

        if record is None:
            raise GameNotFoundError(game_id=game_id)

        return Game(**dict(record))

    async def update_game(self, game_id: int, guild_id: int, **kwargs: typing.Any) -> Game:
        count = len(kwargs)
        if count == 0:
            raise TypeError("0 values passed to update_game")

        # these only come from code, so I feel okay about constructing a query string from them
        columns = ", ".join(kwargs.keys())
        # these are only parameter references and will be processed by asyncpg rather than direct interpolation
        values = ", ".join(f"${n + 3}" for n in range(count))

        row = await self.conn.fetchrow(
            f"UPDATE Games SET ({columns}) = ({values}) WHERE game_id = $1 AND guild_id = $2 RETURNING *;",
            game_id,
            guild_id,
            *kwargs.values(),
        )

        assert row is not None

        return Game(**dict(row))

    async def count_game_characters(self, game_id: int) -> int:
        val = await self.conn.fetchval(
            """
            SELECT COUNT(character_id)
            FROM Characters
            WHERE game_id = $1
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

    async def count_game_players(self, game_id: int) -> int:
        val = await self.conn.fetchval(
            """
            SELECT COUNT((user_id, game_id))
            FROM Players
            WHERE game_id = $1
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

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
            "RETURNING character_id;",
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
