from crescent import Plugin
from hikari import GatewayBot

from modron.config import Config
from modron.db import DBConn


class Model:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.db: DBConn

    async def start(self) -> None:
        self.db = await DBConn.connect(self.config.db_url)

    async def close(self) -> None:
        await self.db.close()


ModronPlugin = Plugin[GatewayBot, Model]
