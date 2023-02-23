from modron.db.conn import Conn, DBConn, convert, with_conn
from modron.db.models import System, SystemLite


class SystemDB(DBConn):
    @with_conn
    @convert(SystemLite)
    async def insert(
        self,
        conn: Conn,
        guild_id: int,
        name: str,
        author_label: str,
        player_label: str,
        emoji_id: int | None = None
    ):
        return await conn.fetchrow(
            """
            INSERT INTO Systems (guild_id, name, author_label, player_label, emoji_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *;
            """,
            guild_id,
            name,
            author_label,
            player_label,
            emoji_id,
        )
    
    @with_conn
    @convert(SystemLite)
    async def get_lite(self, conn: Conn, system_id: int, guild_id: int):
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
    
    @with_conn
    @convert(System)
    async def get(self, conn: Conn, system_id: int, guild_id: int):
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
    async def autocomplete(self, conn: Conn, guild_id: int, partial_name: str) -> list[tuple[str, int]]:
        results = await conn.fetch(
            """
            SELECT
                system_id, name
            FROM Systems
            WHERE
                guild_id = $1
                AND name LIKE $2
            LIMIT 25;
            """,
            guild_id,
            f"{partial_name}%",
        )
        
        return [(r["name"], r["system_id"]) for r in results]
