from modron.db.conn import DBConn, Prep, with_prepared
from modron.db.models import Character


class CharacterDB(DBConn):
    @with_prepared(
        """
        SELECT COUNT(character_id)
        FROM Characters
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
        INSERT INTO Characters
        (game_id, author_id, name, pronouns, image, brief, description)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING character_id;
        """
    )
    async def insert(
        self,
        prep: Prep,
        game_id: int,
        author_id: int,
        name: str,
        brief: str,
        description: str,
        pronouns: str | None = None,
        image: str | None = None,
    ) -> Character:
        row = await prep.fetchrow(
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
