from hikari import GatewayBot, SlashCommand, Snowflake

from modron.config import Config
from modron.db.characters import CharacterDB
from modron.db.conn import Pool, connect
from modron.db.games import GameDB
from modron.db.players import PlayerDB
from modron.db.systems import SystemDB


class Model:
    def __init__(self, config: Config) -> None:
        self.config = config

        self.db_pool: Pool
        self.systems: SystemDB
        self.games: GameDB
        self.players: PlayerDB
        self.characters: CharacterDB

        self.command_ids: dict[str, Snowflake] = {}

    async def start(self, app: GatewayBot) -> None:
        self.db_pool = await connect(self.config.db_url)
        self.systems = SystemDB(self.db_pool)
        self.games = GameDB(self.db_pool)
        self.players = PlayerDB(self.db_pool)
        self.characters = CharacterDB(self.db_pool)

        application = await app.rest.fetch_application()
        commands = await app.rest.fetch_application_commands(application.id)
        self.command_ids = {c.name: c.id for c in commands if isinstance(c, SlashCommand)}

    def mention_command(self, name: str) -> str:
        return f"</{name}:{self.command_ids.get(name.split()[0], None)}>"

    async def close(self) -> None:
        await self.db_pool.close()
