import crescent
import hikari

from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.models import System, SystemLite


class SystemDB(DBConn):
    @with_conn
    @convert(SystemLite)
    async def insert(
        self,
        conn: Conn,
        guild_id: int,
        name: str,
        author_label: str,
        player_label: str,
        description: str | None = None,
        image: str | None = None,
    ):
        return await conn.fetchrow(
            """
            INSERT INTO Systems (guild_id, name, author_label, player_label, description, image)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *;
            """,
            guild_id,
            name,
            author_label,
            player_label,
            description,
            image,
        )

    @with_conn
    @convert(SystemLite)
    async def get_lite(self, conn: Conn, system_id: int, guild_id: int):
        return await conn.fetchrow(
            """
            SELECT *
            FROM Systems
            WHERE
                system_id = $1 AND guild_id = $2;
            """,
            system_id,
            guild_id,
        )

    @with_conn
    @convert(System)
    async def get(self, conn: Conn, system_id: int, guild_id: int):
        return await conn.fetchrow(
            """
            SELECT
                s.*,
                array_remove(array_agg(g), NULL) AS games
            FROM Systems AS s
            LEFT JOIN Games AS g USING (system_id)
            WHERE
                system_id = $1
                AND s.guild_id = $2
                AND g.guild_id = $2
            GROUP BY system_id;
            """,
            system_id,
            guild_id,
        )

    @with_conn
    async def name_exists(self, conn: Conn, guild_id: int, name: str) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                from Systems
                WHERE
                    guild_id = $1
                    AND name = $2
            )
            """,
            guild_id,
            name,
        )

    @with_conn
    async def id_exists(self, conn: Conn, guild_id: int, system_id: int) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                from Systems
                WHERE
                    guild_id = $1
                    AND system_id = $2
            )
            """,
            guild_id,
            system_id,
        )

    @with_conn
    async def update(
        self,
        conn: Conn,
        system_id: int,
        guild_id: int,
        name: str | None = None,
        description: str | None = None,
        author_label: str | None = None,
        player_label: str | None = None,
        image: str | None = None,
    ):
        await conn.execute(
            """
            UPDATE Systems
            SET
                name = COALESCE($3, name),
                description = COALESCE($4, description),
                author_label = COALESCE($5, author_label),
                player_label = COALESCE($6, player_label),
                image = COALESCE($7, image)
            WHERE
                system_id = $1
                AND guild_id = $2;
            """,
            system_id,
            guild_id,
            name,
            description,
            author_label,
            player_label,
            image,
        )

    @with_conn
    async def delete(self, conn: Conn, system_id: int) -> None:
        await conn.execute(
            """
            DELETE
            FROM Systems
            WHERE
                system_id = $1;
            """,
            system_id,
        )

    @with_conn
    async def autocomplete(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                system_id, name
            FROM Systems
            WHERE
                guild_id = $1
                AND name LIKE $2
            LIMIT 25;
            """,
            ctx.guild_id,
            f"{option.value}%",
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]
