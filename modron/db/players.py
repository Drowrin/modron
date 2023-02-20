from modron.db.conn import DBConn, Prep, with_prepared
from modron.db.models import Player


class PlayerDB(DBConn):
    @with_prepared(
        """
        SELECT COUNT((user_id, game_id))
        FROM Players
        WHERE game_id = $1;
        """
    )
    async def count(self, prep: Prep, game_id: int) -> int:
        val = await prep.fetchval(
            game_id,
        )

        assert isinstance(val, int)

        return val

    @with_prepared(
        """
        INSERT INTO Players
        (user_id, game_id, role)
        VALUES ($1, $2, $3)
        RETURNING *;
        """
    )
    async def insert(self, prep: Prep, user_id: int, game_id: int, role: str) -> Player:
        row = await prep.fetchrow(
            user_id,
            game_id,
            role,
        )

        assert row is not None

        return Player(**dict(row))
