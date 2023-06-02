import crescent
import hikari

from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.models import System, SystemLite


class SystemDB(DBConn):
    @convert(SystemLite)
    @with_conn
    async def insert(
        self,
        conn: Conn,
        *,
        guild_id: int,
        name: str,
        abbreviation: str | None = None,
        author_label: str | None = None,
        player_label: str | None = None,
        description: str | None = None,
        image: str | None = None,
        emoji_name: str | None = None,
        emoji_id: int | None = None,
        emoji_animated: bool | None = None,
    ):
        abbreviation = abbreviation or name[:15]
        return await conn.fetchrow(
            """
            INSERT INTO Systems (
                guild_id,
                name,
                abbreviation,
                author_label,
                player_label,
                description,
                image,
                emoji_name,
                emoji_id,
                emoji_animated
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *;
            """,
            guild_id,
            name,
            abbreviation,
            author_label or "Author",
            player_label or "Player",
            description,
            image,
            emoji_name,
            emoji_id,
            emoji_animated,
        )

    @convert(SystemLite)
    @with_conn
    async def get_lite(self, conn: Conn, *, system_id: int, guild_id: int):
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

    @convert(System)
    @with_conn
    async def get(self, conn: Conn, *, system_id: int, guild_id: int):
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
    async def name_exists(self, conn: Conn, *, guild_id: int, name: str) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT NULL
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
    async def id_exists(self, conn: Conn, *, guild_id: int, system_id: int) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT NULL
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
        *,
        system_id: int,
        guild_id: int,
        name: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        abbreviation: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        description: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        author_label: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        player_label: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        image: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        emoji_name: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        emoji_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        emoji_animated: hikari.UndefinedNoneOr[bool] = hikari.UNDEFINED,
    ):
        kwargs = {
            k: v
            for k, v in {
                "name": name,
                "abbreviation": abbreviation,
                "description": description,
                "author_label": author_label,
                "player_label": player_label,
                "image": image,
                "emoji_name": emoji_name,
                "emoji_id": emoji_id,
                "emoji_animated": emoji_animated,
            }.items()
            if v is not hikari.UNDEFINED
        }
        args = kwargs.values()
        columns = ",\n".join(f"{k} = ${i + 3}" for i, k in enumerate(kwargs.keys()))
        await conn.execute(
            f"""
            UPDATE Systems
            SET
                {columns}
            WHERE
                system_id = $1
                AND guild_id = $2;
            """,
            system_id,
            guild_id,
            *args,
        )

    @with_conn
    async def delete(self, conn: Conn, *, system_id: int) -> None:
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
                AND (
                    name ILIKE $2
                    OR abbreviation ILIKE $2
                )
            LIMIT 25;
            """,
            ctx.guild_id,
            f"{option.value}%",
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]
