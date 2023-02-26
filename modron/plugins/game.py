from __future__ import annotations

import asyncio
import typing

import crescent
import flare
import hikari

from modron.exceptions import AutocompleteSelectError, ConfirmationError, EditPermissionError
from modron.models import Game, GameStatus, Response

if typing.TYPE_CHECKING:
    from modron.model import Model

    Plugin = crescent.Plugin[hikari.GatewayBot, Model]
else:
    Plugin = crescent.Plugin[hikari.GatewayBot, None]

plugin = Plugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
)


async def info_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(description=True)],
        "components": [],
    }


async def settings_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(description=True, channels=True, players=True)],
        "components": await asyncio.gather(
            flare.Row(
                ManageChannelsButton.make(game.game_id, game.owner_id),
                EditStatusButton.make(game.game_id, game.owner_id),
                ToggleSeekingPlayers.make(game.game_id, game.owner_id, game.seeking_players),
                AddUsersButton.make(game.game_id, game.owner_id),
            ),
            flare.Row(
                EditButton.make(game.game_id, game.owner_id),
                DeleteButton.make(game.game_id, game.owner_id),
            ),
        ),
    }


async def status_settings_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed()],
        "components": await asyncio.gather(
            flare.Row(StatusSelect.make(game.game_id, game.owner_id, game.status)),
            flare.Row(BackButton.make(game.game_id, game.owner_id)),
        ),
    }


async def channel_settings_view(game: Game, kind: ChannelKind) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(channels=True)],
        "components": await asyncio.gather(
            flare.Row(ChannelKindSelect.make(game.game_id, game.owner_id, kind)),
            flare.Row(GameChannelSelect.make(game.game_id, game.owner_id, kind)),
            flare.Row(BackButton.make(game.game_id, game.owner_id)),
        ),
    }


async def add_user_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(players=True)],
        "components": await asyncio.gather(
            flare.Row(UserSelect.make(game.game_id, game.owner_id)),
            flare.Row(BackButton.make(game.game_id, game.owner_id)),
        ),
    }


ChannelKind = typing.Literal["main", "info", "synopsis", "voice", "category"]


class ChannelKindSelect(flare.TextSelect, min_values=1, max_values=1):
    game_id: int
    owner_id: int
    kind: ChannelKind

    @classmethod
    def make(cls, game_id: int, owner_id: int, kind: ChannelKind) -> typing.Self:
        return cls(game_id, owner_id, kind).set_options(
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
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, typing.cast(ChannelKind, ctx.values[0])),
        )


class GameChannelSelect(flare.ChannelSelect, min_values=0, max_values=1):
    game_id: int
    owner_id: int
    kind: ChannelKind

    @classmethod
    def make(cls, game_id: int, owner_id: int, kind: ChannelKind) -> typing.Self:
        instance = cls(game_id, owner_id, kind)
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
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        await ctx.defer()
        await plugin.model.games.update(
            self.game_id,
            ctx.guild_id,
            ctx.user.id,
            **{f"{self.kind}_channel_id": next((c.id for c in ctx.channels), None)},
        )

        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, self.kind),
        )


class UserSelect(flare.UserSelect, min_values=1, max_values=25, placeholder="Select Players to add"):
    game_id: int
    owner_id: int

    @classmethod
    def make(
        cls,
        game_id: int,
        owner_id: int,
    ) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        await ctx.defer()

        await asyncio.gather(*[plugin.model.players.insert(user.id, self.game_id) for user in ctx.users])

        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(game),
        )


class StatusSelect(flare.TextSelect, min_values=1, max_values=1, placeholder="Change Status"):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int, game_status: GameStatus) -> typing.Self:
        return cls(game_id, owner_id).set_options(
            *[
                hikari.SelectMenuOption(
                    label=status.label,
                    value=status.name.lower(),
                    description=status.description,
                    emoji=hikari.Emoji.parse(status.emoji),
                    is_default=status == game_status,
                )
                for status in GameStatus
            ]
        )

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None

        await plugin.model.games.update(
            self.game_id,
            ctx.guild_id,
            ctx.user.id,
            status=ctx.values[0],
        )
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(game),
        )


class ManageChannelsButton(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id).set_label("Manage Channels")

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, "main"),
        )


class AddUsersButton(flare.Button, label="Add Players", style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await add_user_view(game),
        )


class EditStatusButton(flare.Button, label="Change Status", style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await status_settings_view(game),
        )


class BackButton(flare.Button, label="Back"):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(game),
        )


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    owner_id: int
    seeking_players: bool

    @classmethod
    def make(cls, game_id: int, owner_id: int, seeking_players: bool) -> typing.Self:
        return cls(game_id, owner_id, seeking_players).set_label(
            "Stop Seeking Players" if seeking_players else "Start Seeking Players"
        )

    async def callback(self, ctx: flare.MessageContext):
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        await plugin.model.games.update(
            self.game_id,
            ctx.guild_id,
            ctx.user.id,
            seeking_players=not self.seeking_players,
        )
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(**await settings_view(game))


class EditButton(flare.Button, label="Edit Details"):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get_lite(self.game_id, ctx.guild_id)

        await GameEditModal.make(game.game_id, game.name, game.abbreviation, game.description, game.image).send(
            ctx.interaction
        )


class DeleteButton(flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER):
    game_id: int
    owner_id: int

    @classmethod
    def make(cls, game_id: int, owner_id: int) -> typing.Self:
        return cls(game_id, owner_id)

    async def callback(self, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.owner_id:
            raise EditPermissionError("Game")

        assert ctx.guild_id is not None
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await GameDeleteModal.make(game.game_id).send(ctx.interaction)


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
                ),
            )

            await plugin.model.games.update(
                game_lite.game_id,
                ctx.guild_id,
                ctx.user.id,
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
            **await settings_view(game),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class GameEditModal(flare.Modal, title="Edit Game"):
    game_id: int

    name: flare.TextInput = game_name_text_input
    abbreviation: flare.TextInput = game_abbreviation_text_input
    description: flare.TextInput = game_description_text_input
    image: flare.TextInput = game_image_text_input

    @classmethod
    def make(
        cls,
        game_id: int,
        name: str,
        abbreviation: str | None = None,
        description: str | None = None,
        image: str | None = None,
    ) -> typing.Self:
        instance = cls(game_id)
        instance.name.set_value(name)
        instance.abbreviation.set_value(abbreviation)
        instance.description.set_value(description)
        instance.image.set_value(image)

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
            owner_id=ctx.user.id,
            name=self.name.value,
            abbreviation=self.abbreviation.value,
            # replace '' with None
            description=self.description.value or None,
            image=self.image.value or None,
        )
        game = await plugin.model.games.get(self.game_id, ctx.guild_id)

        await ctx.edit_response(**await settings_view(game))


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
    def make(cls, game_id: int) -> typing.Self:
        return cls(game_id)

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
        # TODO: can't use model in definitions like this
        autocomplete=lambda ctx, option: plugin.model.systems.autocomplete(ctx, option),
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
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.systems.id_exists(ctx.guild_id, system_id):
                raise AutocompleteSelectError()

        await GameCreateModal.make(system_id, self.title, self.auto_setup).send(ctx.interaction)


@plugin.include
@game.child
@crescent.command(name="settings", description="view the settings menu for a specific game")
class GameSettings:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_owned(ctx, option),
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(ctx.guild_id, game_id):
                raise AutocompleteSelectError()

        await ctx.defer(ephemeral=True)

        game = await plugin.model.games.get(game_id, ctx.guild_id)

        await ctx.respond(
            **await settings_view(game),
            ephemeral=True,
        )


@plugin.include
@game.child
@crescent.command(name="info", description="display information for a game")
class GameInfo:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_guild(ctx, option),
    )

    async def callback(self, ctx: crescent.Context) -> None:
        assert ctx.guild_id is not None

        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(ctx.guild_id, game_id):
                raise AutocompleteSelectError()

        await ctx.defer()

        game = await plugin.model.games.get(game_id, ctx.guild_id)

        await ctx.respond(**await info_view(game))
