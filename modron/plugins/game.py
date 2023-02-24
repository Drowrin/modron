from __future__ import annotations

import asyncio
import typing

import crescent
import flare
import hikari

from modron.db import Game, GameLite, GameStatus, Player
from modron.exceptions import AutocompleteSelectError, ConfirmationError, EditPermissionError
from modron.model import ModronPlugin
from modron.plugins.system_management import autocomplete_systems

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


async def player_display(game: Game, player: Player) -> hikari.Embed:
    member = plugin.app.cache.get_member(game.guild_id, player.user_id) or await plugin.app.rest.fetch_member(
        game.guild_id, player.user_id
    )

    return (
        hikari.Embed()
        .set_footer(game.system.player_label if game.system is not None else "Player")
        .set_author(name=member.display_name, icon=member.display_avatar_url)
    )


async def author_display(game: Game) -> hikari.Embed:
    member = plugin.app.cache.get_member(game.guild_id, game.owner_id) or await plugin.app.rest.fetch_member(
        game.guild_id, game.owner_id
    )

    return (
        hikari.Embed()
        .set_footer(game.system.author_label if game.system is not None else "Game Master")
        .set_author(name=member.display_name, icon=member.display_avatar_url)
    )


async def game_display(game: Game) -> typing.Sequence[hikari.Embed]:
    embed = (
        hikari.Embed(
            title=game.name,
            timestamp=game.created_at,
            color=game.status.color,
        )
        .set_footer("Created")
        .set_thumbnail(game.image)
        .add_field("System", game.system.name if game.system is not None else "❌ Deleted System", inline=True)
        .add_field("Status", game.status_str, inline=True)
        .add_field(
            "Seeking Players",
            "✅ Yes" if game.seeking_players else "⏹️ No",
            inline=True,
        )
    )

    if game.description is not None:
        embed.add_field("Description", game.description)

    if game.main_channel_id is not None:
        embed.add_field("Main Channel", f"<#{game.main_channel_id}>", inline=True)

    if game.info_channel_id is not None:
        embed.add_field("Info Channel", f"<#{game.info_channel_id}>", inline=True)

    if game.synopsis_channel_id is not None:
        embed.add_field("Synopsis Channel", f"<#{game.synopsis_channel_id}>", inline=True)

    if game.voice_channel_id is not None:
        embed.add_field("Voice Channel", f"<#{game.voice_channel_id}>", inline=True)

    players = [await player_display(game, player) for player in game.players]

    return [
        embed,
        await author_display(game),
        *players,
    ]


async def game_main_menu(game: Game) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(
            ManageChannelsButton.make(game),
            EditStatusButton.make(game),
            ToggleSeekingPlayers.make(game),
            AddUsersButton.make(game),
        ),
        flare.Row(
            EditButton.make(game),
            DeleteButton.make(game),
        ),
    )


async def game_status_menu(game: Game) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(StatusSelect.make(game)),
        flare.Row(BackButton.make(game)),
    )


async def game_add_user_menu(game: Game) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(UserSelect.make(game)),
        flare.Row(BackButton.make(game)),
    )


async def game_channel_menu(game: Game, kind: ChannelKind) -> typing.Sequence[hikari.api.ComponentBuilder]:
    return await asyncio.gather(
        flare.Row(ChannelKindSelect.make(game, kind)),
        flare.Row(GameChannelSelect.make(game, kind)),
        flare.Row(BackButton.make(game)),
    )


ChannelKind = typing.Literal["main", "info", "synopsis", "voice", "category"]


class ChannelKindSelect(flare.TextSelect, min_values=1, max_values=1):
    game: Game
    kind: ChannelKind

    @classmethod
    def make(cls, game: Game, kind: ChannelKind) -> typing.Self:
        return cls(game, kind).set_options(
            hikari.SelectMenuOption(
                label="Main Channel",
                value="main",
                description="Select the main discussion channel for this game",
                emoji=None,
                is_default=kind == "main",
            ),
            hikari.SelectMenuOption(
                label="Info Channel",
                value="info",
                description="the channel where players can find info and resources",
                emoji=None,
                is_default=kind == "info",
            ),
            hikari.SelectMenuOption(
                label="Synopsis Channel",
                value="synopsis",
                description="the channel where you will post synopsis of each session",
                emoji=None,
                is_default=kind == "synopsis",
            ),
            hikari.SelectMenuOption(
                label="Voice Channel",
                value="voice",
                description="the voice channel that players should join during sessions",
                emoji=None,
                is_default=kind == "voice",
            ),
            hikari.SelectMenuOption(
                label="Category",
                value="category",
                description="the category that contains other channels related to this game",
                emoji=None,
                is_default=kind == "category",
            ),
        )

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        await ctx.edit_response(
            embeds=await game_display(self.game),
            components=await game_channel_menu(self.game, typing.cast(ChannelKind, ctx.values[0])),
        )


class GameChannelSelect(flare.ChannelSelect, min_values=0, max_values=1):
    game: GameLite
    kind: ChannelKind

    @classmethod
    def make(cls, game: GameLite, kind: ChannelKind) -> typing.Self:
        instance = cls(game, kind)
        instance.set_placeholder(f"Select {kind} channel")
        match kind:
            case "main" | "info" | "synopsis":
                instance.set_channel_types(hikari.ChannelType.GUILD_TEXT)
            case "voice":
                instance.set_channel_types(hikari.ChannelType.GUILD_VOICE)
            case "category":
                instance.set_channel_types(hikari.ChannelType.GUILD_CATEGORY)
        return instance

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        key = f"{self.kind}_channel_id"
        channel_id = next((c.id for c in ctx.channels), None)

        await ctx.defer()

        if getattr(self.game, key) != channel_id:
            await plugin.model.games.update(self.game.game_id, ctx.guild_id, **{key: channel_id})

        game = await plugin.model.games.get(self.game.game_id, ctx.guild_id)

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_channel_menu(game, self.kind),
        )


class UserSelect(flare.UserSelect, min_values=1, max_values=25, placeholder="Select Players to add"):
    game: GameLite

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        await ctx.defer()

        await asyncio.gather(*[plugin.model.players.insert(user.id, self.game.game_id) for user in ctx.users])

        game = await plugin.model.games.get(self.game.game_id, ctx.guild_id)

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


class StatusSelect(flare.TextSelect, min_values=1, max_values=1, placeholder="Change Status"):
    game: GameLite

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
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

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


class ManageChannelsButton(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game: Game

    @classmethod
    def make(cls, game: Game) -> typing.Self:
        return cls(game).set_label("Manage Channels")

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await ctx.edit_response(
            components=await game_channel_menu(self.game, "main"),
        )


class AddUsersButton(flare.Button, label="Add Players", style=hikari.ButtonStyle.SECONDARY):
    game: Game

    @classmethod
    def make(cls, game: Game) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await ctx.edit_response(
            components=await game_add_user_menu(self.game),
        )


class EditStatusButton(flare.Button, label="Change Status", style=hikari.ButtonStyle.SECONDARY):
    game: Game

    @classmethod
    def make(cls, game: Game) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await ctx.edit_response(
            components=await game_status_menu(self.game),
        )


class BackButton(flare.Button, label="Back"):
    game: Game

    @classmethod
    def make(cls, game: Game) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await ctx.edit_response(
            components=await game_main_menu(self.game),
        )


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game: GameLite

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
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
    def make(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await GameEditModal.make(self.game).send(ctx.interaction)


class DeleteButton(flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER):
    game: GameLite

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
        return cls(game)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.game.owner_id:
            raise EditPermissionError("Game")

        await GameDeleteModal.make(self.game).send(ctx.interaction)


game_name_text_input = flare.TextInput(
    label="Title",
    placeholder="The full title of the game",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=50,
    required=True,
)

game_abbreviation_text_input = flare.TextInput(
    label="Abbreviation",
    placeholder="A short name that will be used when the full title is too long",
    style=hikari.TextInputStyle.SHORT,
    min_length=1,
    max_length=25,
    required=True,
)

game_description_text_input = flare.TextInput(
    label="Description",
    placeholder="Freeform text that will be displayed in the game info. You can use markdown here.",
    style=hikari.TextInputStyle.PARAGRAPH,
    max_length=1024,
    required=False,
)

game_image_text_input = flare.TextInput(
    label="Image URL",
    placeholder="URL pointing to an image that will be displayed in the game info",
    style=hikari.TextInputStyle.SHORT,
    max_length=256,
    required=False,
)


class GameCreateModal(flare.Modal, title="New Game"):
    system_id: int
    auto_setup: int

    name: flare.TextInput = game_name_text_input
    abbreviation: flare.TextInput = game_abbreviation_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def make(cls, system_id: int, name: str, auto_setup: bool) -> typing.Self:
        instance = cls(system_id, auto_setup)
        instance.name.set_value(name)
        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.abbreviation.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game_lite = await plugin.model.games.insert(
            name=self.name.value,
            abbreviation=self.abbreviation.value,
            system_id=self.system_id,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
            # replace '' with None
            description=self.description.value or None,
            image=self.image.value or None,
        )

        if self.auto_setup:
            category, role = await asyncio.gather(
                plugin.app.rest.create_guild_category(
                    ctx.guild_id,
                    self.abbreviation.value,
                    permission_overwrites=[
                        hikari.PermissionOverwrite(
                            id=ctx.user.id,
                            type=hikari.PermissionOverwriteType.MEMBER,
                            allow=(
                                hikari.Permissions.MANAGE_CHANNELS
                                | hikari.Permissions.SEND_MESSAGES
                                | hikari.Permissions.MANAGE_MESSAGES
                            ),
                        )
                    ],
                ),
                plugin.app.rest.create_role(
                    ctx.guild_id,
                    name=self.abbreviation.value,
                    mentionable=True,
                ),
            )
            
            main, info, synopsis, voice, _ = await asyncio.gather(
                plugin.app.rest.create_guild_text_channel(
                    ctx.guild_id,
                    name="main",
                    category=category.id,
                ),
                plugin.app.rest.create_guild_text_channel(
                    ctx.guild_id,
                    name="info",
                    category=category.id,
                    permission_overwrites=[
                        hikari.PermissionOverwrite(
                            id=ctx.guild_id,  # @everyone
                            type=hikari.PermissionOverwriteType.ROLE,
                            deny=(
                                hikari.Permissions.SEND_MESSAGES
                                | hikari.Permissions.CREATE_PUBLIC_THREADS
                                | hikari.Permissions.CREATE_PRIVATE_THREADS
                                | hikari.Permissions.ADD_REACTIONS
                            ),
                        ),
                    ],
                ),
                plugin.app.rest.create_guild_text_channel(
                    ctx.guild_id,
                    name="synopsis",
                    category=category.id,
                    permission_overwrites=[
                        hikari.PermissionOverwrite(
                            id=ctx.guild_id,  # @everyone
                            type=hikari.PermissionOverwriteType.ROLE,
                            deny=(
                                hikari.Permissions.SEND_MESSAGES
                                | hikari.Permissions.CREATE_PUBLIC_THREADS
                                | hikari.Permissions.CREATE_PRIVATE_THREADS
                                | hikari.Permissions.ADD_REACTIONS
                            ),
                        ),
                    ],
                ),
                plugin.app.rest.create_guild_voice_channel(
                    ctx.guild_id,
                    name="Voice",
                    category=category.id,
                    permission_overwrites=[
                        hikari.PermissionOverwrite(
                            id=ctx.guild_id,  # @everyone
                            type=hikari.PermissionOverwriteType.ROLE,
                            deny=hikari.Permissions.CONNECT,
                        ),
                        hikari.PermissionOverwrite(
                            id=role.id,
                            type=hikari.PermissionOverwriteType.ROLE,
                            allow=hikari.Permissions.CONNECT,
                        ),
                    ],
                ),
                plugin.app.rest.add_role_to_member(
                    ctx.guild_id,
                    ctx.user.id,
                    role.id,
                )
            )

            await plugin.model.games.update(
                game_lite.game_id,
                ctx.guild_id,
                role_id=role.id,
                category_channel_id=category.id,
                main_channel_id=main.id,
                info_channel_id=info.id,
                synopsis_channel_id=synopsis.id,
                voice_channel_id=voice.id,
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
    game_id: int

    name: flare.TextInput = game_name_text_input
    abbreviation: flare.TextInput = game_abbreviation_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
        instance = cls(game.game_id)
        instance.name.set_value(game.name)
        instance.description.set_value(game.description)
        instance.image.set_value(game.image)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.abbreviation.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            name=self.name.value,
            abbreviation=self.name.value,
            # replace '' with None
            description=self.description.value or None,
            image=self.image.value or None,
        )
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            embeds=await game_display(game),
            components=await game_main_menu(game),
        )


class GameDeleteModal(flare.Modal, title="Game Delete Confirmation"):
    game_id: int

    confirmation: flare.TextInput = flare.TextInput(
        label='Please confirm by typing "CONFIRM" in caps',
        placeholder="This can not be undone",
        style=hikari.TextInputStyle.SHORT,
        min_length=1,
        required=True,
    )

    @classmethod
    def make(cls, game: GameLite) -> typing.Self:
        return cls(game.game_id)

    async def callback(self, ctx: flare.ModalContext) -> None:
        if self.confirmation.value != "CONFIRM":
            raise ConfirmationError()

        await plugin.model.games.delete(self.game_id)
        response = await ctx.edit_response("Game successfully deleted!", embeds=[], components=[])
        await asyncio.sleep(5)
        await response.delete()


@plugin.include
@game.child
@crescent.command(name="create", description="create a new game in this server")
class GameCreate:
    title = crescent.option(
        str,
        "The title of the game being created",
    )

    system = crescent.option(
        str,
        "The system this game will be using",
        autocomplete=autocomplete_systems,
    )

    auto_setup = crescent.option(
        bool,
        "Create a custom category, channels, and role with a recommended layout",
        default=True,
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            system_id = int(self.system)
            if not await plugin.model.systems.id_exists(ctx.guild_id, system_id):
                raise AutocompleteSelectError()
        except ValueError as err:
            raise AutocompleteSelectError() from err

        await GameCreateModal.make(system_id, self.title, self.auto_setup).send(ctx.interaction)


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
            if not await plugin.model.games.id_exists(ctx.guild_id, game_id):
                raise AutocompleteSelectError()
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
            if not await plugin.model.games.id_exists(ctx.guild_id, game_id):
                raise AutocompleteSelectError()
        except ValueError as err:
            raise AutocompleteSelectError() from err

        await ctx.defer()

        game = await plugin.model.games.get(game_id, ctx.guild_id)

        await ctx.respond(
            embeds=await game_display(game),
        )
