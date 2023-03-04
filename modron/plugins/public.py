from __future__ import annotations

import typing

import crescent
import hikari

from modron.exceptions import AutocompleteSelectError
from modron.utils import GuildContext

if typing.TYPE_CHECKING:
    from modron.model import Model

    Plugin = crescent.Plugin[hikari.GatewayBot, Model]
else:
    Plugin = crescent.Plugin[hikari.GatewayBot, None]

plugin = Plugin()

info = crescent.Group(
    "info",
    "information",
    dm_enabled=False,
)


@plugin.include
@info.child
@crescent.command(name="system", description="display information for a system")
class SystemInfo:
    name = crescent.option(
        str,
        "the name of the system",
        autocomplete=lambda ctx, option: plugin.model.systems.autocomplete(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        assert ctx.guild_id is not None

        try:
            system_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.systems.id_exists(system_id=system_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await ctx.defer()

        system = await plugin.model.systems.get_lite(system_id=system_id, guild_id=ctx.guild_id)

        await ctx.respond(embed=await plugin.model.render.system(system, description=True))


@plugin.include
@info.child
@crescent.command(name="game", description="display information for a game")
class GameInfo:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_guild(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(game_id=game_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await ctx.defer()

        game = await plugin.model.games.get(game_id=game_id, guild_id=ctx.guild_id)

        await ctx.respond(
            embed=await plugin.model.render.game(game, description=True, guild_resources=True)
        )
