import typing

import crescent

from modron.config import Config
from modron.db import DBConn


class ModronApp(crescent.Bot):
    def __init__(self, config: Config):
        super().__init__(config.discord_token)

        self.config = config
        self.db: DBConn

    # TODO: would prefer a better solution than typing.Any, but I won't be using this function directly anyways
    async def start(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.db = await DBConn.connect(self.config.db_url)
        return await super().start(*args, **kwargs)

    async def close(self) -> None:
        await self.db.close()
        return await super().close()


class ModronPlugin(crescent.Plugin):
    @property
    def app(self) -> ModronApp:
        return typing.cast(ModronApp, super().app)
