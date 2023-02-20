from modron.db.conn import Conn, DBConn, Record, convert, with_conn
from modron.db.models import Game


class GameDB(DBConn):
    @with_conn
    @convert(Game)
    async def insert(
        self,
        conn: Conn,
        name: str,
        description: str,
        system: str,
        guild_id: int,
        owner_id: int,
        image: str | None = None,
    ) -> Record | None:
        return await conn.fetchrow(
            """
            INSERT INTO Games (name, description, system, guild_id, owner_id, image)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *;
            """,
            name,
            description,
            system,
            guild_id,
            owner_id,
            image,
        )

    @with_conn
    @convert(Game)
    async def get(self, conn: Conn, game_id: int, guild_id: int) -> Record | None:
        return await conn.fetchrow(
            """
            SELECT *
            FROM Games
            WHERE game_id = $1 AND guild_id = $2;
            """,
            game_id,
            guild_id,
        )

    @with_conn
    @convert(Game)
    async def get_owned(self, conn: Conn, game_id: int, owner_id: int) -> Record | None:
        return await conn.fetchrow(
            """
            SELECT *
            FROM Games
            WHERE game_id = $1 AND owner_id = $2;
            """,
            game_id,
            owner_id,
        )

    @with_conn
    @convert(Game)
    async def update(
        self,
        conn: Conn,
        game_id: int,
        guild_id: int,
        name: str | None = None,
        description: str | None = None,
        system: str | None = None,
        image: str | None = None,
        status: str | None = None,
        seeking_players: bool | None = None,
    ) -> Record | None:
        return await conn.fetchrow(
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
            """,
            game_id,
            guild_id,
            name,
            description,
            system,
            image,
            status,
            seeking_players,
        )

    @with_conn
    async def delete(self, conn: Conn, game_id: int) -> None:
        await conn.execute(
            """
            DELETE FROM Games
            WHERE game_id = $1;
            """,
            game_id,
        )

    @with_conn
    async def autocomplete_guild(self, conn: Conn, guild_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await conn.fetch(
            """
            SELECT game_id, name FROM Games
            WHERE guild_id = $1 AND name LIKE $2
            LIMIT 25;
            """,
            guild_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    @with_conn
    async def autocomplete_owned(self, conn: Conn, owner_id: int, partial_name: str) -> list[tuple[str, str]]:
        results = await conn.fetch(
            """
            SELECT game_id, name FROM Games
            WHERE owner_id = $1 AND name LIKE $2
            LIMIT 25;
            """,
            owner_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    @with_conn
    async def autocomplete_systems(self, conn: Conn, guild_id: int, partial_name: str) -> list[str]:
        results = await conn.fetch(
            """
            SELECT DISTINCT system FROM Games
            WHERE guild_id = $1 AND system LIKE $2
            LIMIT 25;
            """,
            guild_id,
            f"{partial_name}%",
        )

        return [r[0] for r in results]
