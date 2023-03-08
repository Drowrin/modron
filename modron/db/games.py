import crescent
import hikari
import toolbox

from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.models import Game, GameLite


class GameDB(DBConn):
    @with_conn
    @convert(GameLite)
    async def insert(
        self,
        conn: Conn,
        *,
        guild_id: int,
        author_id: int,
        system_id: int,
        name: str,
        abbreviation: str | None = None,
        description: str | None = None,
        image: str | None = None,
    ):
        abbreviation = abbreviation or name[:25]
        return await conn.fetchrow(
            """
            INSERT INTO Games (name, abbreviation, description, system_id, guild_id, author_id, image)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *;
            """,
            name,
            abbreviation,
            description,
            system_id,
            guild_id,
            author_id,
            image,
        )

    @with_conn
    @convert(GameLite)
    async def get_lite(self, conn: Conn, *, game_id: int, guild_id: int):
        return await conn.fetchrow(
            """
            SELECT
                g.*,
                array_remove(array_agg(s), NULL) AS system
            FROM Games AS g
            LEFT JOIN Systems AS s USING (system_id)
            WHERE
                game_id = $1
                AND g.guild_id = $2
            GROUP BY game_id;
            """,
            game_id,
            guild_id,
        )

    @with_conn
    @convert(Game)
    async def get(self, conn: Conn, *, game_id: int, guild_id: int):
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
            GROUP BY game_id;
            """,
            game_id,
            guild_id,
        )

    @with_conn
    async def name_exists(self, conn: Conn, *, guild_id: int, name: str) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT NULL
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
    async def id_exists(self, conn: Conn, *, guild_id: int, game_id: int, author_id: int | None = None) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS(
                SELECT NULL
                from Games
                WHERE
                    guild_id = $1
                    AND game_id = $2
                    AND author_id = COALESCE($3, author_id)
            )
            """,
            guild_id,
            game_id,
            author_id,
        )

    @with_conn
    async def update(
        self,
        conn: Conn,
        *,
        game_id: int,
        guild_id: int,
        author_id: int,
        name: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        abbreviation: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        description: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        image: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        status: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        seeking_players: hikari.UndefinedNoneOr[bool] = hikari.UNDEFINED,
        category_channel_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        main_channel_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        info_channel_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        synopsis_channel_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        voice_channel_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
        role_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
    ):
        kwargs = {
            k: v
            for k, v in {
                "name": name,
                "abbreviation": abbreviation,
                "description": description,
                "image": image,
                "status": status,
                "seeking_players": seeking_players,
                "category_channel_id": category_channel_id,
                "main_channel_id": main_channel_id,
                "info_channel_id": info_channel_id,
                "synopsis_channel_id": synopsis_channel_id,
                "voice_channel_id": voice_channel_id,
                "role_id": role_id,
            }.items()
            if v is not hikari.UNDEFINED
        }
        args = kwargs.values()
        columns = ",\n".join(f"{k} = ${i + 4}" for i, k in enumerate(kwargs.keys()))
        await conn.execute(
            f"""
            UPDATE Games
            SET
                {columns}
            WHERE
                game_id = $1
                AND guild_id = $2
                AND author_id = $3;
            """,
            game_id,
            guild_id,
            author_id,
            *args,
        )

    @with_conn
    async def delete(self, conn: Conn, *, game_id: int) -> None:
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
    async def autocomplete_guild(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                game_id, name
            FROM Games
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

    @with_conn
    async def autocomplete_editable(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        assert ctx.member is not None
        perms = toolbox.members.calculate_permissions(ctx.member)
        if (perms & hikari.Permissions.MANAGE_GUILD) == hikari.Permissions.MANAGE_GUILD:
            results = await conn.fetch(
                """
                SELECT
                    game_id, name
                FROM Games
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
        else:
            results = await conn.fetch(
                """
                SELECT
                    game_id, name
                FROM Games
                WHERE
                    guild_id = $1
                    AND author_id = $3
                    AND (
                        name ILIKE $2
                        OR abbreviation ILIKE $2
                    )
                LIMIT 25;
                """,
                ctx.guild_id,
                f"{option.value}%",
                ctx.user.id,
            )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]

    @with_conn
    async def autocomplete_joinable(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                g.game_id, g.name
            FROM Games AS g
            WHERE
                g.guild_id = $1
                AND g.author_id != $2
                AND g.seeking_players IS TRUE
                AND (
                    g.name ILIKE $3
                    OR g.abbreviation ILIKE $3
                )
                AND NOT EXISTS (
                    SELECT NULL
                    FROM Players AS p
                    WHERE
                        p.game_id = g.game_id
                        AND p.user_id = $2
                )
            LIMIT 25;
            """,
            ctx.guild_id,
            ctx.user.id,
            f"{option.value}%",
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]

    @with_conn
    async def autocomplete_joined(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                g.game_id, g.name
            FROM Games AS g
            WHERE
                g.guild_id = $1
                AND EXISTS (
                    SELECT NULL
                    FROM Players AS p
                    WHERE
                        p.game_id = g.game_id
                        AND p.user_id = $2
                )
                AND (
                    g.name ILIKE $3
                    OR g.abbreviation ILIKE $3
                )
            LIMIT 25;
            """,
            ctx.guild_id,
            ctx.user.id,
            f"{option.value}%",
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]
    
    @with_conn
    async def autocomplete_involved(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                g.game_id, g.name
            FROM Games AS g
            WHERE
                g.guild_id = $1
                AND (
                    g.author_id = $2
                    OR EXISTS (
                        SELECT NULL
                        FROM Players AS p
                        WHERE
                            p.game_id = g.game_id
                            AND p.user_id = $2
                    )
                )
                AND (
                    g.name ILIKE $3
                    OR g.abbreviation ILIKE $3
                )
            LIMIT 25;
            """,
            ctx.guild_id,
            ctx.user.id,
            f"{option.value}%",
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]
