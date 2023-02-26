import functools
import typing
from pathlib import Path

import hikari

from modron.config import Config
from modron.model import Model

ReturnT = typing.TypeVar("ReturnT")
SpecT = typing.ParamSpec("SpecT")
SigT = typing.Callable[
    typing.Concatenate[hikari.api.RESTClient, Model, SpecT], typing.Coroutine[typing.Any, typing.Any, ReturnT]
]


def with_model(f: SigT[SpecT, ReturnT]) -> typing.Callable[SpecT, typing.Coroutine[typing.Any, typing.Any, ReturnT]]:
    @functools.wraps(f)
    async def inner(*args: SpecT.args, **kwargs: SpecT.kwargs) -> ReturnT:
        config = Config.load(Path("dev.config.yml"))
        model = Model(config)
        app = hikari.RESTApp()

        await app.start()

        async with app.acquire(config.discord_token, token_type=hikari.TokenType.BOT) as rest:
            await model.start(rest)

            out = await f(rest, model, *args, **kwargs)

        await app.close()
        return out

    return inner
