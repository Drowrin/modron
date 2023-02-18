import typing

from modron.db.conn import DBConn
from modron.db.models import Game
from modron.exceptions import GameNotFoundError


class GameDB(DBConn):
    async def insert(
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

    async def get(self, game_id: int, guild_id: int) -> Game:
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

    async def get_owned(self, game_id: int, owner_id: int) -> Game:
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

    async def update(self, game_id: int, guild_id: int, **kwargs: typing.Any) -> Game:
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

    async def autocomplete_guild(self, guild_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await self.conn.fetch(
            "SELECT game_id, name FROM Games WHERE guild_id = $1 AND name LIKE $2 LIMIT 25;",
            guild_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    async def autocomplete_owned(self, owner_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await self.conn.fetch(
            "SELECT game_id, name FROM Games WHERE owner_id = $1 AND name LIKE $2 LIMIT 25;",
            owner_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    async def autocomplete_systems(self, guild_id: int, partial_name: str) -> list[str]:
        results = await self.conn.fetch(
            "SELECT DISTINCT system FROM Games WHERE guild_id = $1 AND system LIKE $2 LIMIT 25;",
            guild_id,
            f"{partial_name}%",
        )

        return [r[0] for r in results]
