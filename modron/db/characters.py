import crescent
import hikari

from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.models import Character


class CharacterDB(DBConn):
    @with_conn
    async def count(self, conn: Conn, *, game_id: int) -> int:
        val = await conn.fetchval(
            """
            SELECT COUNT(character_id)
            FROM Characters
            WHERE game_id = $1;
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

    @convert(Character)
    @with_conn
    async def insert(
        self,
        conn: Conn,
        *,
        game_id: int,
        author_id: int,
        name: str,
        brief: str | None = None,
        description: str | None = None,
        pronouns: str | None = None,
        image: str | None = None,
    ):
        return await conn.fetchrow(
            """
            INSERT INTO Characters
            (game_id, author_id, name, pronouns, image, brief, description)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *;
            """,
            game_id,
            author_id,
            name,
            pronouns,
            image,
            brief,
            description,
        )

    @with_conn
    @convert(Character)
    async def get(self, conn: Conn, *, character_id: int, guild_id: int):
        return await conn.fetchrow(
            """
            SELECT *
            FROM Characters AS c
            WHERE
                c.character_id = $1
                AND (
                    EXISTS (
                        SELECT NULL
                        FROM Players AS p
                        INNER JOIN Games AS g USING (game_id)
                        WHERE
                            g.guild_id = $2
                            AND p.character_id = $1
                    )
                );
            """,
            character_id,
            guild_id,
        )

    @with_conn
    async def update(
        self,
        conn: Conn,
        *,
        character_id: int,
        user_id: int,
        name: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        pronouns: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        image: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        brief: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
        description: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
    ):
        kwargs = {
            k: v
            for k, v in {
                "name": name,
                "pronouns": pronouns,
                "image": image,
                "brief": brief,
                "description": description,
            }.items()
            if v is not hikari.UNDEFINED
        }
        args = kwargs.values()
        columns = ",\n".join(f"c.{k} = ${i + 3}" for i, k in enumerate(kwargs.keys()))
        await conn.execute(
            f"""
            UPDATE Characters AS c
            SET
                {columns}
            WHERE
                c.character_id = $1
                AND (
                    c.author_id = $2
                    OR EXISTS (
                        SELECT NULL
                        FROM Players AS p
                        WHERE
                            p.character_id = $1
                            AND p.user_id = $2
                    )
                );
            """,
            character_id,
            user_id,
            *args,
        )

    @with_conn
    async def delete(self, conn: Conn, *, character_id: int) -> None:
        await conn.execute(
            """
            DELETE
            FROM Characters
            WHERE
                character_id = $1;
            """,
            character_id,
        )

    @with_conn
    async def autocomplete_viewable(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                c.character_id, c.name
            FROM Characters AS c
            WHERE
                c.name ILIKE $1
                AND EXISTS (
                    SELECT NULL
                    FROM Players AS p
                    INNER JOIN Games AS g USING (game_id)
                    WHERE
                        p.character_id = c.character_id
                        AND g.guild_id = $2
                )
            LIMIT 25;
            """,
            f"{option.value}%",
            ctx.guild_id,
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]

    @with_conn
    async def autocomplete_editable(
        self, conn: Conn, ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
    ) -> list[hikari.CommandChoice]:
        results = await conn.fetch(
            """
            SELECT
                c.character_id, c.name
            FROM Characters AS c
            WHERE
                c.name ILIKE $1
                AND EXISTS (
                    SELECT NULL
                    FROM Players AS p
                    INNER JOIN Games AS g USING (game_id)
                    WHERE
                        p.character_id = c.character_id
                        AND g.guild_id = $2
                        AND (
                            c.author_id = $3
                            OR p.user_id = $3
                        )
                )
            LIMIT 25;
            """,
            f"{option.value}%",
            ctx.guild_id,
            ctx.user.id,
        )

        return [hikari.CommandChoice(name=r[1], value=str(r[0])) for r in results]
