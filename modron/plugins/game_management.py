from __future__ import annotations

import asyncio
import typing

import crescent
import flare
import hikari
import hikari.api

from modron.db.models import Game, GameStatus
from modron.exceptions import GameError, GameNotFoundError, GamePermissionError
from modron.model import ModronPlugin

plugin = ModronPlugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.MANAGE_MESSAGES,
)


@plugin.include
@crescent.catch_command(GameError, GamePermissionError, GameNotFoundError)
async def on_game_error(exc: GameError, ctx: crescent.Context) -> None:
    await ctx.respond(**exc.to_response_args())


class GameConverter(flare.Converter[Game]):
    async def to_str(self, obj: Game) -> str:
        return f"{obj.guild_id}:{obj.game_id}"

    async def from_str(self, obj: str) -> Game:
        guild_id, game_id = obj.split(":")
        return await plugin.model.db.get_game(int(game_id), int(guild_id))


flare.add_converter(Game, GameConverter)


async def game_display(game: Game) -> typing.Sequence[hikari.Embed]:
    char_count = await plugin.model.db.count_game_characters(game.game_id)
    player_count = await plugin.model.db.count_game_players(game.game_id)

    embed = (
        hikari.Embed(
            title=game.name,
            description=game.description,
            timestamp=game.created_at,
            color=game.status.color,
        )
        .set_footer(game.status_str)
        .set_image(game.image)
        .set_thumbnail(game.thumb)
        .add_field("System", game.system, inline=True)
        .add_field("Characters", str(char_count), inline=True)
        .add_field("Players", str(player_count), inline=True)
    )

    return [embed]


async def game_main_menu(game: Game) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(StatusSelect.from_game(game)),
        flare.Row(EditButton.from_game(game), ToggleSeekingPlayers.from_game(game)),
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
        game = await plugin.model.db.update_game(self.game.game_id, ctx.guild_id, status=ctx.values[0])

        await ctx.edit_response(embeds=await game_display(game), components=await game_main_menu(game))


class ToggleSeekingPlayers(flare.Button):
    game: Game

    @classmethod
    def from_game(cls, game: Game) -> ToggleSeekingPlayers:
        return cls(game).set_label("Stop Seeking Players" if game.seeking_players else "Start Seeking Players")

    async def callback(self, ctx: flare.MessageContext):
        if ctx.user.id != self.game.owner_id:
            raise GamePermissionError(self.game.game_id)

        assert ctx.guild_id is not None
        game = await plugin.model.db.update_game(
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

game_image_text_input = flare.TextInput(
    label="Image URL",
    style=hikari.TextInputStyle.SHORT,
    min_length=None,
    max_length=256,
    required=False,
)

game_thumb_text_input = flare.TextInput(
    label="Thumbnail URL",
    style=hikari.TextInputStyle.SHORT,
    min_length=None,
    max_length=256,
    required=False,
)


class GameCreateModal(flare.Modal):
    system: str

    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input
    thumb: flare.TextInput = game_thumb_text_input

    @classmethod
    def from_system(cls, system: str) -> GameCreateModal:
        return cls(system).set_title(f"New {system} Game")

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game = await plugin.model.db.insert_game(
            name=self.name.value,
            description=self.description.value,
            system=self.system,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
            # replace '' with None
            image=self.image.value or None,
            thumb=self.thumb.value or None,
        )

        await ctx.respond(
            "You can view this menu again with `/game menu`",
            embeds=await game_display(game),
            components=await game_main_menu(game),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class GameEditModal(flare.Modal, title="Edit Game"):
    game: Game

    name: flare.TextInput = game_name_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input
    thumb: flare.TextInput = game_thumb_text_input

    @classmethod
    def from_game(cls, game: Game):
        instance = cls(game)
        instance.name.set_value(game.name)
        instance.description.set_value(game.description)
        if game.image is not None:
            instance.image.set_value(game.image)
        if game.thumb is not None:
            instance.thumb.set_value(game.thumb)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game = await plugin.model.db.update_game(
            game_id=self.game.game_id,
            guild_id=ctx.guild_id,
            name=self.name.value,
            description=self.description.value,
            # replace '' with None
            image=self.image.value or None,
            thumb=self.thumb.value or None,
        )

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


async def autocomplete_systems(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    results = await plugin.model.db.conn.fetch(
        "SELECT DISTINCT system FROM Games WHERE guild_id = $1 AND system LIKE $2 LIMIT 25;",
        ctx.guild_id,
        f"{option.value}%",
    )

    return [hikari.CommandChoice(name=r[0], value=r[0]) for r in results]


@plugin.include
@game.child
@crescent.command(name="create", description="create a new game in this server")
class GameCreate:
    system = crescent.option(
        str, "The system this game will be using", autocomplete=autocomplete_systems, max_length=36
    )

    async def callback(self, ctx: crescent.Context) -> None:
        await GameCreateModal.from_system(self.system).send(ctx.interaction)


async def autocomplete_guild_games(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    results = await plugin.model.db.conn.fetch(
        "SELECT game_id, name FROM Games WHERE guild_id = $1 AND name LIKE $2 LIMIT 25;",
        ctx.guild_id,
        f"{option.value}%",
    )

    return [hikari.CommandChoice(name=r["name"], value=str(r["game_id"])) for r in results]


async def autocomplete_owned_games(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    results = await plugin.model.db.conn.fetch(
        "SELECT game_id, name FROM Games WHERE owner_id = $1 AND name LIKE $2 LIMIT 25;",
        ctx.user.id,
        f"{option.value}%",
    )

    return [hikari.CommandChoice(name=r["name"], value=str(r["game_id"])) for r in results]


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

        game = await plugin.model.db.get_owned_game(game_id, ctx.user.id)

        await ctx.respond(
            embeds=await game_display(game),
            components=await game_main_menu(game),
            ephemeral=True,
        )


@plugin.include
@game.child
@crescent.command(name="info", description="")
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

        game = await plugin.model.db.get_game(game_id, ctx.guild_id)

        await ctx.respond(
            embeds=await game_display(game),
        )
