import asyncpg
from crescent import Plugin
from hikari import GatewayBot

from modron.config import Config
from modron.db import CharacterDB, GameDB, PlayerDB, connect


class Model:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.db: asyncpg.Connection[asyncpg.Record]
        self.games: GameDB
        self.players: PlayerDB
        self.characters: CharacterDB

    async def start(self) -> None:
        self.db = await connect(self.config.db_url)
        self.games = GameDB(self.db)
        self.players = PlayerDB(self.db)
        self.characters = CharacterDB(self.db)

    async def close(self) -> None:
        await self.db.close()


ModronPlugin = Plugin[GatewayBot, Model]
