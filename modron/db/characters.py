from modron.db.conn import Conn, DBConn, with_conn
from modron.db.models import Character


class CharacterDB(DBConn):
    @with_conn
    async def count(self, conn: Conn, game_id: int) -> int:
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

    @with_conn
    async def insert(
        self,
        conn: Conn,
        game_id: int,
        author_id: int,
        name: str,
        brief: str,
        description: str,
        pronouns: str | None = None,
        image: str | None = None,
    ) -> Character:
        row = await conn.fetchrow(
            """
            INSERT INTO Characters
            (game_id, author_id, name, pronouns, image, brief, description)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING character_id;
            """,
            game_id,
            author_id,
            name,
            pronouns,
            image,
            brief,
            description,
        )

        assert row is not None

        return Character(**dict(row))
