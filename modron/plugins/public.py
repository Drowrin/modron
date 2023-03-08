from __future__ import annotations

import asyncio

import crescent
import hikari

from modron.exceptions import AutocompleteSelectError
from modron.model import ModronPlugin
from modron.utils import GuildContext

plugin = ModronPlugin()

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
            embed=await plugin.model.render.game(game, description=True, guild_resources=True, players=True)
        )


@plugin.include
@crescent.command(name="join", description="join a game in this server", dm_enabled=False)
class JoinGame:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_joinable(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(game_id=game_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await ctx.defer(ephemeral=True)

        game, _ = await asyncio.gather(
            plugin.model.games.get_lite(game_id=game_id, guild_id=ctx.guild_id),
            plugin.model.players.insert(user_id=ctx.user.id, game_id=game_id),
        )

        await plugin.model.fab.apply_role_to(game, ctx.user.id)

        await ctx.respond(
            content=f"Successfully joined {game.name}!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )


@plugin.include
@crescent.command(name="leave", description="leave a game in this server", dm_enabled=False)
class LeaveGame:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_joined(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(game_id=game_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await ctx.defer(ephemeral=True)

        game, _ = await asyncio.gather(
            plugin.model.games.get_lite(game_id=game_id, guild_id=ctx.guild_id),
            plugin.model.players.delete(user_id=ctx.user.id, game_id=game_id),
        )

        await plugin.model.fab.remove_role_from(game, ctx.user.id)

        await ctx.respond(
            content=f"Successfully left {game.name}!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
