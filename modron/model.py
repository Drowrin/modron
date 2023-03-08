import hikari

from modron.config import Config
from modron.db.characters import CharacterDB
from modron.db.conn import Pool, connect
from modron.db.games import GameDB
from modron.db.players import PlayerDB
from modron.db.systems import SystemDB
from modron.fabricate import Fabricator
from modron.render import Renderer


class Model:
    def __init__(self, config: Config) -> None:
        self.config = config

        self.db_pool: Pool
        self.systems: SystemDB
        self.games: GameDB
        self.players: PlayerDB
        self.characters: CharacterDB

        self.app_id: hikari.Snowflake

        self.render: Renderer
        self.fab: Fabricator

    async def start(self, client: hikari.api.RESTClient, cache: hikari.api.Cache | None = None) -> None:
        self.db_pool = await connect(self.config.db_url)
        self.systems = SystemDB(self.db_pool)
        self.games = GameDB(self.db_pool)
        self.players = PlayerDB(self.db_pool)
        self.characters = CharacterDB(self.db_pool)

        application = await client.fetch_application()
        self.app_id = application.id

        commands = await client.fetch_application_commands(application.id)
        command_ids = {c.name: c.id for c in commands if isinstance(c, hikari.SlashCommand)}

        self.render = Renderer(command_ids, client, cache)

        self.fab = Fabricator(self.app_id, self.games, client)

    async def close(self) -> None:
        await self.db_pool.close()
