import hikari

from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.models import Player


class PlayerDB(DBConn):
    @with_conn
    async def count(self, conn: Conn, *, game_id: int) -> int:
        val = await conn.fetchval(
            """
            SELECT COUNT((user_id, game_id))
            FROM Players
            WHERE game_id = $1;
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

    @with_conn
    async def insert(self, conn: Conn, *, user_id: int, game_id: int):
        await conn.execute(
            """
            INSERT INTO Players
            (user_id, game_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, game_id)
                DO NOTHING;
            """,
            user_id,
            game_id,
        )

    @with_conn
    @convert(Player)
    async def get(self, conn: Conn, *, game_id: int, user_id: int):
        return await conn.fetchrow(
            """
            SELECT *
            FROM Players
            WHERE
                game_id = $1
                AND user_id = $2;
            """,
            game_id,
            user_id,
        )

    @with_conn
    async def update(
        self,
        conn: Conn,
        *,
        game_id: int,
        user_id: int,
        character_id: hikari.UndefinedNoneOr[int] = hikari.UNDEFINED,
    ) -> None:
        if character_id is hikari.UNDEFINED:
            return
        await conn.execute(
            """
            UPDATE Players
            SET
                character_id = COALESCE($3, character_id)
            WHERE
                game_id = $1
                AND user_id = $2;
            """,
            game_id,
            user_id,
            character_id,
        )

    @with_conn
    async def delete(self, conn: Conn, *, game_id: int, user_id: int) -> None:
        await conn.execute(
            """
            DELETE
            FROM Players
            WHERE
                game_id = $1
                AND user_id = $2;
            """,
            game_id,
            user_id,
        )

    @with_conn
    async def exists(self, conn: Conn, *, game_id: int, user_id: int) -> bool:
        return await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT NULL
                FROM Players
                WHERE
                    user_id = $2
                    AND game_id = $1;
            )
            """,
            game_id,
            user_id,
        )
