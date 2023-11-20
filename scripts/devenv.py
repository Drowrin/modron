import os
import sys

sys.path.insert(0, os.getcwd())

import functools
import typing
from pathlib import Path

import hikari

from modron.config import Config
from modron.model import Model

ReturnT = typing.TypeVar("ReturnT")
InjectedT = typing.TypeVar("InjectedT")
SpecT = typing.ParamSpec("SpecT")
SigT = typing.Callable[
    typing.Concatenate[hikari.api.RESTClient, InjectedT, SpecT], typing.Coroutine[typing.Any, typing.Any, ReturnT]
]
OutSigT = typing.Callable[SpecT, typing.Coroutine[typing.Any, typing.Any, ReturnT]]


def with_model(f: SigT[Model, SpecT, ReturnT]) -> OutSigT[SpecT, ReturnT]:
    @functools.wraps(f)
    async def inner(*args: SpecT.args, **kwargs: SpecT.kwargs) -> ReturnT:
        config = Config.load(Path("dev.config.yml"))
        model = Model(config)
        app = hikari.RESTApp()

        await app.start()

        try:
            async with app.acquire(config.discord_token, token_type=hikari.TokenType.BOT) as rest:
                await model.start(rest)

                return await f(rest, model, *args, **kwargs)
        finally:
            await app.close()
            await model.close()

    return inner


async def reset_schema(model: Model):
    await model.db_pool.execute("DROP TABLE IF EXISTS Players;")
    await model.db_pool.execute("DROP TABLE IF EXISTS Characters;")
    await model.db_pool.execute("DROP TABLE IF EXISTS Games;")
    await model.db_pool.execute("DROP TABLE IF EXISTS Systems;")
    await model.db_pool.execute("DROP TYPE IF EXISTS game_status;")

    with open(Path("modron/db/schema.sql")) as f:
        await model.db_pool.execute(f.read())
