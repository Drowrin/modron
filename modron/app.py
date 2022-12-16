import typing

import crescent

from modron.config import Config


class ModronApp(crescent.Bot):
    def __init__(self, config: Config):
        super().__init__(config.discord_token)

        self.config = config


class ModronPlugin(crescent.Plugin):
    @property
    def app(self) -> ModronApp:
        return typing.cast(ModronApp, super().app)
