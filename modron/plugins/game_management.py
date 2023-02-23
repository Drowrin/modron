from __future__ import annotations

import asyncio
import typing

import crescent
import flare
import hikari

from modron.db import Game, GameLite, GameStatus
from modron.exceptions import AutocompleteSelectError, ConfirmationError, EditPermissionError
from modron.model import ModronPlugin

plugin = ModronPlugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
)


class GameConverter(flare.Converter[Game]):
    async def to_str(self, obj: Game) -> str:
        return f"{obj.guild_id}:{obj.game_id}"

    async def from_str(self, obj: str) -> Game:
        guild_id, game_id = obj.split(":")
        return await plugin.model.games.get(int(game_id), int(guild_id))


class GameLiteConverter(flare.Converter[GameLite]):
    async def to_str(self, obj: GameLite) -> str:
        return f"{obj.guild_id}:{obj.game_id}"

    async def from_str(self, obj: str) -> GameLite:
        guild_id, game_id = obj.split(":")
        return await plugin.model.games.get_lite(int(game_id), int(guild_id))


flare.add_converter(Game, GameConverter)
flare.add_converter(GameLite, GameLiteConverter)


async def game_display(game: Game) -> typing.Sequence[hikari.Embed]:
    embed = (
        hikari.Embed(
            title=game.name,
            timestamp=game.created_at,
            color=game.status.color,
        )
        .set_footer("Created")
        .set_thumbnail(game.image)
        .add_field("System", game.system.name, inline=True)
        .add_field("Status", game.status_str, inline=True)
    )

    if game.seeking_players:
        embed.add_field("Seeking Players", "✅ Yes", inline=True)

    embed.add_field("Description", game.description)

    for player in game.players:
        user = plugin.app.cache.get_member(game.guild_id, player.user_id) or await plugin.app.rest.fetch_member(
            game.guild_id, player.user_id
        )

        character = player.get_character_in(game)

        role = game.system.player_label

        if character is not None:
            role = f"{role}: {character.name}"

        embed.add_field(user.display_name, role, inline=True)

    return [embed]


async def game_main_menu(game: Game) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(StatusSelect.from_game(game)),
        flare.Row(
            ToggleSeekingPlayers.from_game(game),
        ),
        flare.Row(
            EditButton.from_game(game),
            DeleteButton.from_game(game),
        ),
    )


class StatusSelect(flare.TextSelect, min_values=1, max_values=1, placeholder="Change Status"):
    game: GameLite

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        return cls(game).set_options(
            *[
                hikari.SelectMenuOption(
                    label=status.label,
                    value=status.name.lower(),
                    description=status.description,
                    emoji=hikari.Emoji.parse(status.emoji),
                    is_default=status == game.status,
                )
                for status in GameStatus
            ]
        )

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        await plugin.model.games.update(self.game.game_id, ctx.guild_id, status=ctx.values[0])
        game = await plugin.model.games.get(self.game.game_id, ctx.guild_id)

        await ctx.edit_response(embeds=await game_display(game), components=await game_main_menu(game))


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game: GameLite

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        return cls(game).set_label("Stop Seeking Players" if game.seeking_players else "Start Seeking Players")

    async def callback(self, ctx: flare.MessageContext):
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        await plugin.model.games.update(self.game.game_id, ctx.guild_id, seeking_players=not self.game.seeking_players)
        game = await plugin.model.games.get(self.game.game_id, ctx.guild_id)

        await ctx.edit_response(embeds=await game_display(game), components=await game_main_menu(game))


class EditButton(flare.Button, label="Edit Details"):
    game: GameLite

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await GameEditModal.from_game(self.game).send(ctx.interaction)


class DeleteButton(flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER):
    game: GameLite

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await GameDeleteModal.from_game(self.game).send(ctx.interaction)


game_name_text_input = flare.TextInput(
    label="Title",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=50,
    required=True,
)

game_description_text_input = flare.TextInput(
    label="Description",
    style=hikari.TextInputStyle.PARAGRAPH,
    min_length=1,
    max_length=1024,
    required=True,
)

game_system_text_input = flare.TextInput(
    label="System",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=30,
    required=True,
)

game_image_text_input = flare.TextInput(
    label="Image URL",
    style=hikari.TextInputStyle.SHORT,
    min_length=None,
    max_length=256,
    required=False,
)


class GameCreateModal(flare.Modal, title="New Game"):
    system_id: int

    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game_lite = await plugin.model.games.insert(
            name=self.name.value,
            description=self.description.value,
            system_id=self.system_id,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
            # replace '' with None
            image=self.image.value or None,
        )
        game = await plugin.model.games.get(
            game_lite.game_id,
            ctx.guild_id,
        )

        await ctx.respond(
            f"You can view this menu again with {plugin.model.mention_command('game settings')}",
            embeds=await game_display(game),
            components=await game_main_menu(game),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class GameEditModal(flare.Modal, title="Edit Game"):
    game: GameLite

    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        instance = cls(game)
        instance.name.set_value(game.name)
        instance.description.set_value(game.description)
        instance.image.set_value(game.image)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        kwargs = {
            k: v
            for k in ["name", "description", "image"]
            if (v := getattr(self, k).value or None) != getattr(self.game, k)
        }

        if len(kwargs) == 0:
            return  # nothing to update

        await plugin.model.games.update(game_id=self.game.game_id, guild_id=ctx.guild_id, **kwargs)
        game = await plugin.model.games.get(self.game.game_id, ctx.guild_id)

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


class GameDeleteModal(flare.Modal, title="Game Delete Confirmation"):
    game: GameLite

    confirmation: flare.TextInput = flare.TextInput(
        label='Please confirm by typing "CONFIRM" in caps',
        placeholder="This can not be undone",
        style=hikari.TextInputStyle.SHORT,
        min_length=1,
        required=True,
    )

    @classmethod
    def from_game(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.ModalContext) -> None:
        if self.confirmation.value != "CONFIRM":
            raise ConfirmationError()

        await plugin.model.games.delete(self.game.game_id)
        response = await ctx.edit_response("Game successfully deleted!", embeds=[], components=[])
        await asyncio.sleep(5)
        await response.delete()


async def autocomplete_systems(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    assert ctx.guild_id is not None

    results = await plugin.model.systems.autocomplete(ctx.guild_id, str(option.value))

    return [hikari.CommandChoice(name=name, value=str(system_id)) for name, system_id in results]


@plugin.include
@game.child
@crescent.command(name="create", description="create a new game in this server")
class GameCreate:
    system = crescent.option(
        str,
        "The system this game will be using (you can change this later)",
        autocomplete=autocomplete_systems,
        max_length=36,
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            system_id = int(self.system)
        except ValueError as err:
            raise AutocompleteSelectError() from err

        system = await plugin.model.systems.get_lite(system_id, ctx.guild_id)

        await GameCreateModal(system_id=system.system_id).send(ctx.interaction)


async def autocomplete_guild_games(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    assert ctx.guild_id is not None

    results = await plugin.model.games.autocomplete_guild(ctx.guild_id, str(option.value))

    return [hikari.CommandChoice(name=name, value=str(game_id)) for name, game_id in results]


async def autocomplete_owned_games(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    results = await plugin.model.games.autocomplete_owned(ctx.user.id, str(option.value))

    return [hikari.CommandChoice(name=name, value=str(game_id)) for name, game_id in results]


@plugin.include
@game.child
@crescent.command(name="settings", description="view the settings menu for a specific game")
class GameSettings:
    name = crescent.option(str, "the name of the game", autocomplete=autocomplete_owned_games)

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err

        await ctx.defer(ephemeral=True)

        game = await plugin.model.games.get(game_id, ctx.guild_id, ctx.user.id)

        await ctx.respond(
            embeds=await game_display(game),
            components=await game_main_menu(game),
            ephemeral=True,
        )


@plugin.include
@game.child
@crescent.command(name="info", description="display information for a game")
class GameInfo:
    name = crescent.option(str, "the name of the game", autocomplete=autocomplete_guild_games)

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err

        await ctx.defer()

        game = await plugin.model.games.get(game_id, ctx.guild_id)

        await ctx.respond(
            embeds=await game_display(game),
        )
