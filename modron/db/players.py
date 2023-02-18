from modron.db.conn import DBConn


class PlayerDB(DBConn):
    async def count(self, game_id: int) -> int:
        val = await self.conn.fetchval(
            """
            SELECT COUNT((user_id, game_id))
            FROM Players
            WHERE game_id = $1
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

    async def insert(self, *, user_id: int, game_id: int, role: str, character_id: int | None = None) -> None:
        await self.conn.execute(
            "INSERT INTO Players (user_id, game_id, character_id, role)" "VALUES ($1, $2, $3, $4);",
            user_id,
            game_id,
            character_id,
            role,
        )
