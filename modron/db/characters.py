from modron.db.conn import DBConn


class CharacterDB(DBConn):
    async def count(self, game_id: int) -> int:
        val = await self.conn.fetchval(
            """
            SELECT COUNT(character_id)
            FROM Characters
            WHERE game_id = $1
            """,
            game_id,
        )

        assert isinstance(val, int)

        return val

    async def insert(
        self,
        *,
        game_id: int,
        author_id: int,
        name: str,
        brief: str,
        description: str,
        pronouns: str | None = None,
        image: str | None = None,
    ) -> int:
        character_id = await self.conn.fetchval(
            "INSERT INTO Characters (game_id, author_id, name, pronouns, image, brief, description)"
            "VALUES ($1, $2, $3, $4, $5, $6, $7)"
            "RETURNING character_id;",
            game_id,
            author_id,
            name,
            pronouns,
            image,
            brief,
            description,
        )

        assert isinstance(character_id, int)

        return character_id
