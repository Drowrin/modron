from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.db.models import Game, GameLite


class GameDB(DBConn):
    @with_conn
    @convert(GameLite)
    async def insert(
        self,
        conn: Conn,
        name: str,
        abbreviation: str,
        system_id: int,
        guild_id: int,
        owner_id: int,
        description: str | None = None,
        image: str | None = None,
    ):
        return await conn.fetchrow(
            """
            INSERT INTO Games (name, abbreviation, description, system_id, guild_id, owner_id, image)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *;
            """,
            name,
            abbreviation,
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
        abbreviation: str | None = None,
        description: str | None = None,
        image: str | None = None,
        status: str | None = None,
        seeking_players: bool | None = None,
        category_channel_id: int | None = None,
        main_channel_id: int | None = None,
        info_channel_id: int | None = None,
        synopsis_channel_id: int | None = None,
        voice_channel_id: int | None = None,
        role_id: int | None = None,
    ):
        await conn.execute(
            """
            UPDATE Games
            SET
                name = COALESCE($3, name),
                abbreviation = COALESCE($4, abbreviation),
                description = COALESCE($5, description),
                image = COALESCE($6, image),
                status = COALESCE($7, status),
                seeking_players = COALESCE($8, seeking_players),
                category_channel_id = COALESCE($9, category_channel_id),
                main_channel_id = COALESCE($10, main_channel_id),
                info_channel_id = COALESCE($11, info_channel_id),
                synopsis_channel_id = COALESCE($12, synopsis_channel_id),
                voice_channel_id = COALESCE($13, voice_channel_id),
                role_id = COALESCE($14, role_id)
            WHERE
                game_id = $1
                AND guild_id = $2;
            """,
            game_id,
            guild_id,
            name,
            abbreviation,
            description,
            image,
            status,
            seeking_players,
            category_channel_id,
            main_channel_id,
            info_channel_id,
            synopsis_channel_id,
            voice_channel_id,
            role_id,
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
