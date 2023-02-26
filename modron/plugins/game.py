from __future__ import annotations

import asyncio
import functools
import typing

import crescent
import flare
import hikari

from modron.exceptions import AutocompleteSelectError, ConfirmationError, EditPermissionError
from modron.models import Game, GameLite, GameStatus, Response
from modron.utils import GuildContext

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


class AuthorAware(typing.Protocol):
    author_id: int


AuthorAwareT = typing.TypeVar("AuthorAwareT", bound=AuthorAware)
SignatureT = typing.Callable[[AuthorAwareT, flare.MessageContext], typing.Coroutine[typing.Any, typing.Any, None]]


def only_author(f: SignatureT[AuthorAwareT]):
    @functools.wraps(f)
    async def inner(self: AuthorAwareT, ctx: flare.MessageContext) -> None:
        if ctx.user.id != self.author_id:
            raise EditPermissionError("Game")
        return await f(self, ctx)

    return inner


async def info_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(description=True, guild_resources=True)],
        "components": [],
    }


async def settings_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(abbreviation=True, description=True, guild_resources=True, players=True)],
        "components": await asyncio.gather(
            flare.Row(
                ManageChannelsButton.make(game.game_id, game.author_id),
                EditStatusButton.make(game.game_id, game.author_id),
                RoleButton.make(game.game_id, game.author_id, game.role_id),
                ToggleSeekingPlayers.make(game.game_id, game.author_id, game.seeking_players),
                AddUsersButton.make(game.game_id, game.author_id),
            ),
            flare.Row(
                EditButton.make(game.game_id, game.author_id),
                DeleteButton.make(game.game_id, game.author_id),
            ),
        ),
    }


async def status_settings_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed()],
        "components": await asyncio.gather(
            flare.Row(StatusSelect.make(game.game_id, game.author_id, game.status)),
            flare.Row(BackButton.make(game.game_id, game.author_id)),
        ),
    }


async def channel_settings_view(game: Game, kind: ChannelKind) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(guild_resources=True)],
        "components": await asyncio.gather(
            flare.Row(ChannelKindSelect.make(game.game_id, game.author_id, kind)),
            flare.Row(GameChannelSelect.make(game.game_id, game.author_id, kind)),
            flare.Row(BackButton.make(game.game_id, game.author_id)),
        ),
    }


async def add_users_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await game.embed(players=True)],
        "components": await asyncio.gather(
            flare.Row(UserSelect.make(game.game_id, game.author_id)),
            flare.Row(BackButton.make(game.game_id, game.author_id)),
        ),
    }


ChannelKind = typing.Literal["main", "info", "synopsis", "voice", "category"]


class ChannelKindSelect(flare.TextSelect, min_values=1, max_values=1):
    game_id: int
    author_id: int
    kind: ChannelKind

    @classmethod
    def make(cls, game_id: int, author_id: int, kind: ChannelKind) -> typing.Self:
        return cls(game_id, author_id, kind).set_options(
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

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, typing.cast(ChannelKind, ctx.values[0])),
        )


class GameChannelSelect(flare.ChannelSelect, min_values=0, max_values=1):
    game_id: int
    author_id: int
    kind: ChannelKind

    @classmethod
    def make(cls, game_id: int, author_id: int, kind: ChannelKind) -> typing.Self:
        instance = cls(game_id, author_id, kind)
        instance.set_placeholder(f"Select {kind} channel")
        match kind:
            case "main" | "info" | "synopsis":
                instance.set_channel_types(hikari.ChannelType.GUILD_TEXT)
            case "voice":
                instance.set_channel_types(hikari.ChannelType.GUILD_VOICE)
            case "category":
                instance.set_channel_types(hikari.ChannelType.GUILD_CATEGORY)
        return instance

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        await ctx.defer()
        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            **{f"{self.kind}_channel_id": next((c.id for c in ctx.channels), None)},
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, self.kind),
        )


class UserSelect(flare.UserSelect, min_values=1, max_values=25, placeholder="Select Players to add"):
    game_id: int
    author_id: int

    @classmethod
    def make(
        cls,
        game_id: int,
        author_id: int,
    ) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        await ctx.defer()

        await asyncio.gather(
            *[plugin.model.players.insert(user_id=user.id, game_id=self.game_id) for user in ctx.users]
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await add_users_view(game),
        )


class StatusSelect(flare.TextSelect, min_values=1, max_values=1, placeholder="Change Status"):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int, game_status: GameStatus) -> typing.Self:
        return cls(game_id, author_id).set_options(
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

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            status=ctx.values[0],
        )
        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await status_settings_view(game),
        )


class ManageChannelsButton(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id).set_label("Manage Channels")

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await channel_settings_view(game, "main"),
        )


class AddUsersButton(flare.Button, label="Add Players", style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await add_users_view(game),
        )


class EditStatusButton(flare.Button, label="Change Status", style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await status_settings_view(game),
        )


class BackButton(flare.Button, label="Back"):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(game),
        )


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int
    seeking_players: bool

    @classmethod
    def make(cls, game_id: int, author_id: int, seeking_players: bool) -> typing.Self:
        return cls(game_id, author_id, seeking_players).set_label(
            "Stop Seeking Players" if seeking_players else "Start Seeking Players"
        )

    @only_author
    async def callback(self, ctx: flare.MessageContext):
        assert ctx.guild_id is not None

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            seeking_players=not self.seeking_players,
        )
        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(**await settings_view(game))


class RoleButton(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int
    role_id: int | None
    
    @classmethod
    def make(cls, game_id: int, author_id: int, role_id: int | None) -> typing.Self:
        return cls(game_id, author_id, role_id).set_label(
            "Unlink Role" if role_id is not None else "Create Role"
        )
    
    @only_author
    async def callback(self, ctx: flare.MessageContext):
        assert ctx.guild_id is not None
        
        if self.role_id is None:
            game_lite = await plugin.model.games.get_lite(game_id=self.game_id, guild_id=ctx.guild_id)
            role = await game_lite.create_role()
            role_id = role.id
        else:
            role_id = None
        
        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=self.author_id,
            role_id=role_id,
        )
        
        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)
        
        await ctx.edit_response(**await settings_view(game))


class EditButton(flare.Button, label="Edit Details"):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get_lite(game_id=self.game_id, guild_id=ctx.guild_id)

        await GameEditModal.make(game).send(ctx.interaction)


class DeleteButton(flare.Button, label="Delete", style=hikari.ButtonStyle.DANGER):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await GameDeleteModal.make(game.game_id).send(ctx.interaction)


game_name_text_input = flare.TextInput(
    label="Title",
    placeholder="The full title of the game",
    style=hikari.TextInputStyle.SHORT,
    max_length=50,
    required=True,
)

game_abbreviation_text_input = flare.TextInput(
    label="Abbreviation",
    placeholder="An optional short name",
    style=hikari.TextInputStyle.SHORT,
    max_length=25,
    required=False,
)

game_description_text_input = flare.TextInput(
    label="Description",
    placeholder="Freeform text that will be displayed in the game info.\nYou *can* use **markdown** here.",
    style=hikari.TextInputStyle.PARAGRAPH,
    max_length=1024,
    required=False,
)

game_image_text_input = flare.TextInput(
    label="Image URL",
    placeholder="URL pointing to an image",
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
    def make(cls, system_id: int, name: str, abbreviation: str, auto_setup: bool) -> typing.Self:
        instance = cls(system_id, auto_setup)
        instance.name.set_value(name)
        instance.abbreviation.set_value(abbreviation)
        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        game_lite = await plugin.model.games.insert(
            name=self.name.value,
            system_id=self.system_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            # replace '' with None
            abbreviation=self.abbreviation.value or None,
            description=self.description.value or None,
            image=self.image.value or None,
        )

        if self.auto_setup:
            await game_lite.full_setup()

        game = await plugin.model.games.get(
            game_id=game_lite.game_id,
            guild_id=ctx.guild_id,
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
    def make(cls, game: GameLite) -> typing.Self:
        instance = cls(game.game_id)
        instance.name.set_value(game.name)
        instance.abbreviation.set_value(game.abbreviation)
        instance.description.set_value(game.description)
        instance.image.set_value(game.image)

        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            name=self.name.value,
            # replace '' with None
            abbreviation=self.abbreviation.value or None,
            description=self.description.value or None,
            image=self.image.value or None,
        )
        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(**await settings_view(game))


class GameDeleteModal(flare.Modal, title="Game Delete Confirmation"):
    game_id: int

    confirmation: flare.TextInput = flare.TextInput(
        label='Please confirm by typing "CONFIRM" in caps',
        placeholder="This can not be undone",
        style=hikari.TextInputStyle.SHORT,
        required=True,
    )

    @classmethod
    def make(cls, game_id: int) -> typing.Self:
        return cls(game_id)

    async def callback(self, ctx: flare.ModalContext) -> None:
        if self.confirmation.value != "CONFIRM":
            raise ConfirmationError()

        await plugin.model.games.delete(game_id=self.game_id)
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
        max_length=50,
    )

    system = crescent.option(
        str,
        "The system this game will be using",
        autocomplete=lambda ctx, option: plugin.model.systems.autocomplete(ctx, option),
    )

    auto_setup = crescent.option(
        bool,
        "Create a custom category, channels, and role with a recommended layout",
        default=True,
    )

    async def callback(self, ctx: GuildContext) -> None:
        assert ctx.guild_id is not None

        try:
            system_id = int(self.system)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.systems.id_exists(system_id=system_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await GameCreateModal.make(system_id, self.title, self.title[:25], self.auto_setup).send(ctx.interaction)


@plugin.include
@game.child
@crescent.command(name="settings", description="view the settings menu for a specific game")
class GameSettings:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_owned(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        assert ctx.guild_id is not None

        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(game_id=game_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await ctx.defer(ephemeral=True)

        game = await plugin.model.games.get(game_id=game_id, guild_id=ctx.guild_id)

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

        await ctx.respond(**await info_view(game))
