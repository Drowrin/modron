from modron.db.conn import Conn, DBConn, Record, convert, with_conn
from modron.db.models import Player


class PlayerDB(DBConn):
    @with_conn
    async def count(self, conn: Conn, game_id: int) -> int:
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
    @convert(Player)
    async def insert(self, conn: Conn, user_id: int, game_id: int, role: str) -> Record | None:
        return await conn.fetchrow(
            """
            INSERT INTO Players
            (user_id, game_id, role)
            VALUES ($1, $2, $3)
            RETURNING *;
            """,
            user_id,
            game_id,
            role,
        )
