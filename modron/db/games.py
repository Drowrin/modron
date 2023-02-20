from modron.db.conn import DBConn, Prep, with_prepared
from modron.db.models import Game
from modron.exceptions import GameNotFoundError


class GameDB(DBConn):
    @with_prepared(
        "INSERT INTO Games (name, description, system, guild_id, owner_id, image)"
        "VALUES ($1, $2, $3, $4, $5, $6)"
        "RETURNING *;"
    )
    async def insert(
        self,
        prep: Prep,
        name: str,
        description: str,
        system: str,
        guild_id: int,
        owner_id: int,
        image: str | None = None,
    ) -> Game:
        row = await prep.fetchrow(
            name,
            description,
            system,
            guild_id,
            owner_id,
            image,
        )

        assert row is not None

        return Game(**dict(row))

    @with_prepared(
        """
        SELECT *
        FROM Games
        WHERE game_id = $1 AND guild_id = $2;
        """
    )
    async def get(self, prep: Prep, game_id: int, guild_id: int) -> Game:
        record = await prep.fetchrow(
            game_id,
            guild_id,
        )

        if record is None:
            raise GameNotFoundError(game_id)

        return Game(**dict(record))

    @with_prepared(
        """
        SELECT *
        FROM Games
        WHERE game_id = $1 AND owner_id = $2;
        """
    )
    async def get_owned(self, prep: Prep, game_id: int, owner_id: int) -> Game:
        record = await prep.fetchrow(
            game_id,
            owner_id,
        )

        if record is None:
            raise GameNotFoundError(game_id=game_id)

        print({**record})

        return Game(**dict(record))

    @with_prepared(
        """
        UPDATE Games
        SET
            name = COALESCE($3, name),
            description = COALESCE($4, description),
            system = COALESCE($5, system),
            image = COALESCE($6, image),
            status = COALESCE($7, status),
            seeking_players = COALESCE($8, seeking_players)
        WHERE game_id = $1 AND guild_id = $2
        RETURNING *;
        """
    )
    async def update(
        self,
        prep: Prep,
        game_id: int,
        guild_id: int,
        name: str | None = None,
        description: str | None = None,
        system: str | None = None,
        image: str | None = None,
        status: str | None = None,
        seeking_players: bool | None = None,
    ) -> Game:
        row = await prep.fetchrow(game_id, guild_id, name, description, system, image, status, seeking_players)

        assert row is not None

        return Game(**dict(row))

    @with_prepared(
        """
        DELETE FROM Games
        WHERE game_id = $1;
        """
    )
    async def delete(self, prep: Prep, game_id: int) -> None:
        await prep.fetchval(
            game_id,
        )

    @with_prepared(
        """
        SELECT game_id, name FROM Games
        WHERE guild_id = $1 AND name LIKE $2
        LIMIT 25;
        """
    )
    async def autocomplete_guild(self, prep: Prep, guild_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await prep.fetch(
            guild_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    @with_prepared(
        """
        SELECT game_id, name FROM Games
        WHERE owner_id = $1 AND name LIKE $2
        LIMIT 25;
        """
    )
    async def autocomplete_owned(self, prep: Prep, owner_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await prep.fetch(
            owner_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    @with_prepared(
        """
        SELECT DISTINCT system FROM Games
        WHERE guild_id = $1 AND system LIKE $2
        LIMIT 25;
        """
    )
    async def autocomplete_systems(self, prep: Prep, guild_id: int, partial_name: str) -> list[str]:
        results = await prep.fetch(
            guild_id,
            f"{partial_name}%",
        )

        return [r[0] for r in results]
