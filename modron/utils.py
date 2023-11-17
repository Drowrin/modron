import typing

import crescent
import hikari

from modron.model import Model


async def get_me(app: hikari.RESTAware) -> hikari.OwnUser:
    """
    Get the bot user from the cache if available, otherwise fetch it.
    """
    if isinstance(app, hikari.CacheAware):
        return app.cache.get_me() or await app.rest.fetch_my_user()
    else:
        return await app.rest.fetch_my_user()


class GuildContext(crescent.Context):
    # these are always available in commands that are not allowed in DMs
    guild_id: hikari.Snowflake  # type: ignore
    member: hikari.Member  # type: ignore


class Response(typing.TypedDict):
    content: hikari.UndefinedNoneOr[str]
    embeds: typing.Sequence[hikari.Embed]
    components: typing.Sequence[hikari.api.ComponentBuilder]


class ModronPlugin(crescent.Plugin[hikari.GatewayBot, Model]):
    ...
