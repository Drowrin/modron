from __future__ import annotations

import asyncio
import typing

import crescent
import flare
import hikari
import hikari.api

from modron.db import Game, GameStatus
from modron.exceptions import ConfirmationError, GamePermissionError
from modron.model import ModronPlugin

plugin = ModronPlugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
)


async def game_display(game: Game) -> typing.Sequence[hikari.Embed]:
    char_count = await plugin.model.characters.count(game.game_id)
    player_count = await plugin.model.players.count(game.game_id)

    embed = (
        hikari.Embed(
            title=game.name,
            description=game.description,
            timestamp=game.created_at,
            color=game.status.color,
        )
        .set_footer(game.status_str)
        .set_thumbnail(game.image)
        .add_field("System", game.system, inline=True)
        .add_field("Characters", str(char_count), inline=True)
        .add_field("Players", str(player_count), inline=True)
    )

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
    game: Game

    @classmethod
    def from_game(cls, game: Game) -> StatusSelect:
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
            raise GamePermissionError(self.game.game_id)

        assert ctx.guild_id is not None
        game = await plugin.model.games.update(self.game.game_id, ctx.guild_id, status=ctx.values[0])

        await ctx.edit_response(embeds=await game_display(game), components=await game_main_menu(game))


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game: Game

    @classmethod
    def from_game(cls, game: Game) -> ToggleSeekingPlayers:
        return cls(game).set_label("Stop Seeking Players" if game.seeking_players else "Start Seeking Players")

    async def callback(self, ctx: flare.MessageContext):
        if ctx.user.id != self.game.owner_id:
            raise GamePermissionError(self.game.game_id)

        assert ctx.guild_id is not None
        game = await plugin.model.games.update(
            self.game.game_id, ctx.guild_id, seeking_players=not self.game.seeking_players
        )

        await ctx.edit_response(embeds=await game_display(game), components=await game_main_menu(game))


class EditButton(flare.Button, label="Edit Details"):
    game: Game

    @classmethod
    def from_game(cls, game: Game) -> EditButton:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise GamePermissionError(self.game.game_id)

        await GameEditModal.from_game(self.game).send(ctx.interaction)


class DeleteButton(flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER):
    game: Game

    @classmethod
    def from_game(cls, game: Game) -> DeleteButton:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise GamePermissionError(self.game.game_id)

        await GameDeleteModal.from_game(self.game).send(ctx.interaction)


game_name_text_input = flare.TextInput(
    label="Title",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=100,
    required=True,
)

game_description_text_input = flare.TextInput(
    label="Description",
    style=hikari.TextInputStyle.PARAGRAPH,
    min_length=1,
    max_length=4000,
    required=True,
)

game_system_text_input = flare.TextInput(
    label="System",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=35,
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
    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    system: flare.TextInput = game_system_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def from_details(
        cls,
        system: str,
        name: str | None = None,
        description: str | None = None,
        image: str | None = None,
    ) -> GameCreateModal:
        instance = cls()
        instance.name.set_value(name)
        instance.description.set_value(description)
        instance.system.set_value(system)
        instance.image.set_value(image)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        assert self.system.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game = await plugin.model.games.insert(
            name=self.name.value,
            description=self.description.value,
            system=self.system.value,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
            # replace '' with None
            image=self.image.value or None,
        )

        await ctx.respond(
            f"You can view this menu again with {plugin.model.mention_command('game settings')}",
            embeds=await game_display(game),
            components=await game_main_menu(game),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class GameEditModal(flare.Modal, title="Edit Game"):
    game: Game

    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    system: flare.TextInput = game_system_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def from_game(cls, game: Game) -> GameEditModal:
        instance = cls(game)
        instance.name.set_value(game.name)
        instance.description.set_value(game.description)
        instance.system.set_value(game.system)
        instance.image.set_value(game.image)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        assert self.system.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        kwargs = {
            k: v
            for k in ["name", "description", "system", "image"]
            if (v := getattr(self, k).value or None) != getattr(self.game, k)
        }

        if len(kwargs) == 0:
            return  # nothing to update

        game = await plugin.model.games.update(game_id=self.game.game_id, guild_id=ctx.guild_id, **kwargs)

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


class GameDeleteModal(flare.Modal, title="Game Delete Confirmation"):
    game: Game

    confirmation: flare.TextInput = flare.TextInput(
        label='Please confirm by typing "CONFIRM" in caps',
        placeholder="This can not be undone",
        style=hikari.TextInputStyle.SHORT,
        min_length=1,
        required=True,
    )

    @classmethod
    def from_game(cls, game: Game) -> GameDeleteModal:
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

    results = await plugin.model.games.autocomplete_systems(ctx.guild_id, str(option.value))

    return [hikari.CommandChoice(name=r, value=r) for r in results]


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
    title = crescent.option(
        str,
        "The display title of the game (you can change this later)",
        max_length=100,
        default=None,
    )
    description = crescent.option(
        str,
        "The description of the game (you can change this later)",
        max_length=4000,
        default=None,
    )
    image = crescent.option(
        str,
        "URL pointing to an image that will be used as a banner for the game (you can change this later)",
        max_length=256,
        default=None,
    )

    async def callback(self, ctx: crescent.Context) -> None:
        await GameCreateModal.from_details(
            system=self.system,
            name=self.title,
            description=self.description,
            image=self.image,
        ).send(ctx.interaction)


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
        try:
            game_id = int(self.name)
        except ValueError:
            await ctx.respond(
                "Please select an autocomplete suggestion",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        await ctx.defer(ephemeral=True)

        game = await plugin.model.games.get_owned(game_id, ctx.user.id)

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
        except ValueError:
            await ctx.respond(
                "Please select an autocomplete suggestion",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
            return

        await ctx.defer()

        game = await plugin.model.games.get(game_id, ctx.guild_id)

        await ctx.respond(
            embeds=await game_display(game),
        )
