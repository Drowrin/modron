from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.db.models import Game, GameLite


class GameDB(DBConn):
    @with_conn
    @convert(GameLite)
    async def insert(
        self,
        conn: Conn,
        name: str,
        system_id: int,
        guild_id: int,
        owner_id: int,
        description: str | None = None,
        image: str | None = None,
    ):
        return await conn.fetchrow(
            """
            INSERT INTO Games (name, description, system_id, guild_id, owner_id, image)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *;
            """,
            name,
            description,
            system_id,
            guild_id,
            owner_id,
            image,
        )

    @with_conn
    @convert(GameLite)
    async def get_lite(self, conn: Conn, game_id: int, guild_id: int):
        return await conn.fetchrow(
            """
            SELECT *
            FROM Games
            WHERE
                game_id = $1
                AND guild_id = $2;
            """,
            game_id,
            guild_id,
        )

    @with_conn
    @convert(Game)
    async def get(self, conn: Conn, game_id: int, guild_id: int, owner_id: int | None = None):
        return await conn.fetchrow(
            """
            SELECT
                g.*,
                array_remove(array_agg(s), NULL) AS system,
                array_remove(array_agg(c), NULL) AS characters,
                array_remove(array_agg(p), NULL) AS players
            FROM Games AS g
            LEFT JOIN Systems AS s USING (system_id)
            LEFT JOIN Characters AS c USING (game_id)
            LEFT JOIN Players AS p USING (game_id)
            WHERE
                game_id = $1
                AND g.guild_id = $2
                AND ($3::bigint IS NULL OR owner_id = $3::bigint)
            GROUP BY game_id;
            """,
            game_id,
            guild_id,
            owner_id,
        )

    @with_conn
    async def name_exists(self, conn: Conn, guild_id: int, name: str) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                from Games
                WHERE
                    guild_id = $1
                    AND name = $2
            )
            """,
            guild_id,
            name,
        )

    @with_conn
    async def id_exists(self, conn: Conn, guild_id: int, game_id: int) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                from Games
                WHERE
                    guild_id = $1
                    AND game_id = $2
            )
            """,
            guild_id,
            game_id,
        )

    @with_conn
    async def update(
        self,
        conn: Conn,
        game_id: int,
        guild_id: int,
        name: str | None = None,
        description: str | None = None,
        image: str | None = None,
        status: str | None = None,
        seeking_players: bool | None = None,
    ):
        await conn.execute(
            """
            UPDATE Games
            SET
                name = COALESCE($3, name),
                description = COALESCE($4, description),
                image = COALESCE($5, image),
                status = COALESCE($6, status),
                seeking_players = COALESCE($7, seeking_players)
            WHERE
                game_id = $1
                AND guild_id = $2;
            """,
            game_id,
            guild_id,
            name,
            description,
            image,
            status,
            seeking_players,
        )

    @with_conn
    async def delete(self, conn: Conn, game_id: int) -> None:
        await conn.execute(
            """
            DELETE
            FROM Games
            WHERE
                game_id = $1;
            """,
            game_id,
        )

    @with_conn
    async def autocomplete_guild(self, conn: Conn, guild_id: int, partial_name: str) -> list[tuple[str, int]]:
        results = await conn.fetch(
            """
            SELECT
                game_id, name
            FROM Games
            WHERE
                guild_id = $1
                AND name LIKE $2
            LIMIT 25;
            """,
            guild_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]

    @with_conn
    async def autocomplete_owned(self, conn: Conn, owner_id: int, partial_name: str) -> list[tuple[str, int]]:
        results = await conn.fetch(
            """
            SELECT
                game_id, name
            FROM Games
            WHERE
                owner_id = $1
                AND name LIKE $2
            LIMIT 25;
            """,
            owner_id,
            f"{partial_name}%",
        )

        return [(r["name"], r["game_id"]) for r in results]
