from __future__ import annotations

import asyncio
import functools
import typing

import crescent
import flare
import hikari
import toolbox

from modron.exceptions import (
    AutocompleteSelectError,
    ConfirmationError,
    EditPermissionError,
    ModronError,
    NotFoundError,
)
from modron.models import Game, GameLite, GameStatus
from modron.utils import GuildContext, Response

if typing.TYPE_CHECKING:
    from modron.model import Model

    Plugin = crescent.Plugin[hikari.GatewayBot, Model]
else:
    Plugin = crescent.Plugin[hikari.GatewayBot, None]

MANAGE_GAME_PERMISSIONS = hikari.Permissions.MANAGE_GUILD

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
    async def inner(self: AuthorAwareT, ctx: flare.MessageContext) -> None:
        assert ctx.member is not None
        perms = toolbox.members.calculate_permissions(ctx.member)
        if (perms & MANAGE_GAME_PERMISSIONS) == MANAGE_GAME_PERMISSIONS:
            return await f(self, ctx)
        if ctx.user.id == self.author_id:
            return await f(self, ctx)
        raise EditPermissionError("Game")

    return inner


async def settings_view(member: hikari.Member, game: Game) -> Response:
    buttons: list[flare.Button] = [
        SwitchView.make("manage_details", game.game_id, game.author_id).set_label("Game Details").set_emoji("📄"),
        SwitchView.make("player_settings", game.game_id, game.author_id).set_label("Player Settings").set_emoji("👥"),
    ]

    perms = toolbox.members.calculate_permissions(member)
    if perms.any(hikari.Permissions.MANAGE_CHANNELS, hikari.Permissions.MANAGE_ROLES):
        buttons.append(
            SwitchView.make(
                "manage_connections",
                game.game_id,
                game.author_id,
                extra="main",
            )
            .set_label("Connected Role/Channels")
            .set_emoji("🔗")
        )

    return {
        "content": None,
        "embeds": [
            await plugin.model.render.game(
                game, abbreviation=True, description=True, guild_resources=True, players=True
            )
        ],
        "components": await asyncio.gather(
            flare.Row(*buttons),
        ),
    }


async def manage_details_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await plugin.model.render.game(game, abbreviation=True, description=True)],
        "components": await asyncio.gather(
            flare.Row(StatusSelect.make(game.game_id, game.author_id, game.status)),
            flare.Row(
                EditButton.make(game.game_id, game.author_id),
                SwitchView.make("settings", game.game_id, game.author_id).set_label("Back"),
            ),
        ),
    }


def get_kind_overwrites(game: GameLite, kind: ConnectionKind) -> typing.Sequence[hikari.PermissionOverwrite]:
    match kind:
        case "main" | "role":
            return []
        case "info" | "synopsis":
            return plugin.model.create.read_only_overwrites(game)
        case "voice":
            return plugin.model.create.voice_overwrites(game)
        case "category":
            return plugin.model.create.category_overwrites(game)


def overwrite_to_text(overwrite: hikari.PermissionOverwrite, guild_id: hikari.Snowflakeish) -> str:
    assert isinstance(overwrite.type, hikari.PermissionOverwriteType)
    match overwrite.type:
        case hikari.PermissionOverwriteType.ROLE:
            if guild_id == overwrite.id:
                name = "@everyone"
            else:
                name = f"<@&{overwrite.id}>"
        case hikari.PermissionOverwriteType.MEMBER:
            name = f"<@{overwrite.id}>"

    description = "\n".join([f"✅ `{a.name}`" for a in overwrite.allow] + [f"❌ `{d.name}`" for d in overwrite.deny])

    return f"{name}\n{description}"


async def manage_connections_view(member: hikari.Member, kind: ConnectionKind, game: Game) -> Response:
    overwrites = get_kind_overwrites(game, kind)

    embeds = [await plugin.model.render.game(game, guild_resources=True)]

    buttons: list[flare.Button] = [SwitchView.make("settings", game.game_id, game.author_id).set_label("Back")]

    if len(overwrites) > 0:
        buttons.append(OverwritesButton.make(game.game_id, game.author_id, kind))
        embeds.append(
            hikari.Embed(
                title="Recommended Permissions",
                description=(
                    "The following permissions are recommended for this channel.\n"
                    "Clieck `Apply Permissions` to apply them to the selected channel."
                    "\n\n"
                )
                + "\n\n".join(overwrite_to_text(ow, game.guild_id) for ow in overwrites),
            )
        )

    match kind:
        case "role":
            select = GameRoleSelect.make(game.game_id, game.author_id)
        case _:
            select = GameChannelSelect.make(game.game_id, game.author_id, kind)

    return {
        "content": None,
        "embeds": embeds,
        "components": await asyncio.gather(
            flare.Row(ConnectionKindSelect.make(member, game.game_id, game.author_id, kind)),
            flare.Row(select),
            flare.Row(*buttons),
        ),
    }


async def players_settings_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await plugin.model.render.game(game, players=True)],
        "components": await asyncio.gather(
            flare.Row(
                ToggleSeekingPlayers.make(game.game_id, game.author_id, game.seeking_players),
                SwitchView.make("add_players", game.game_id, game.author_id).set_label("Add Players").set_emoji("➕"),
                SwitchView.make("manage_players", game.game_id, game.author_id)
                .set_label("Manage Players")
                .set_emoji("🔧"),
            ),
            flare.Row(
                SwitchView.make("settings", game.game_id, game.author_id).set_label("Back"),
            )
        ),
    }


async def add_players_view(game: Game) -> Response:
    return {
        "content": None,
        "embeds": [await plugin.model.render.game(game, players=True)],
        "components": await asyncio.gather(
            flare.Row(AddPlayerSelect.make(game.game_id, game.author_id)),
            flare.Row(
                SwitchView.make("player_settings", game.game_id, game.author_id).set_label("Back"),
            ),
        ),
    }


async def manage_players_view(selected: hikari.Snowflake | None, game: Game) -> Response:
    buttons: list[flare.Button] = [SwitchView.make("player_settings", game.game_id, game.author_id).set_label("Back")]

    if selected is not None:
        buttons.append(RemovePlayerButton.make(game.game_id, game.author_id, selected))

    return {
        "content": None,
        "embeds": [await plugin.model.render.game(game, players=True)],
        "components": await asyncio.gather(
            flare.Row(
                await ManagePlayerSelect.make(game, selected),
            ),
            flare.Row(*buttons),
        ),
    }


ViewName = typing.Literal[
    "settings", "add_players", "player_settings", "manage_players", "manage_details", "manage_connections"
]


class SwitchView(flare.Button, style=hikari.ButtonStyle.SECONDARY):
    game_id: int
    author_id: int
    view: ViewName
    extra: str

    @classmethod
    def make(cls, view: ViewName, game_id: int, author_id: int, *, extra: str = "") -> typing.Self:
        return cls(game_id, author_id, view, extra)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None
        assert ctx.member is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        match self.view:
            case "settings":
                v = functools.partial(settings_view, ctx.member)
            case "add_players":
                v = add_players_view
            case "player_settings":
                v = players_settings_view
            case "manage_players":
                if self.extra:
                    v = functools.partial(manage_players_view, hikari.Snowflake(self.extra))
                else:
                    v = functools.partial(manage_players_view, None)
            case "manage_details":
                v = manage_details_view
            case "manage_connections":
                v = functools.partial(manage_connections_view, ctx.member, typing.cast(ConnectionKind, self.extra))

        await ctx.edit_response(
            **await v(game),
        )


ChannelKind = typing.Literal["main", "info", "synopsis", "voice", "category"]
ConnectionKind = typing.Literal["role"] | ChannelKind


class ConnectionKindSelect(flare.TextSelect, min_values=1, max_values=1):
    game_id: int
    author_id: int
    kind: ConnectionKind

    @classmethod
    def make(cls, member: hikari.Member, game_id: int, author_id: int, kind: ConnectionKind) -> typing.Self:
        options: list[hikari.SelectMenuOption] = []

        perms = toolbox.members.calculate_permissions(member)

        if perms.all(hikari.Permissions.MANAGE_CHANNELS):
            options += [
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
            ]

        if perms.all(hikari.Permissions.MANAGE_ROLES):
            options += [
                hikari.SelectMenuOption(
                    label="Role",
                    value="role",
                    description="the role that will be assigned to all players",
                    emoji=None,
                    is_default=kind == "role",
                )
            ]

        return cls(game_id, author_id, kind).set_options(*options)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None
        assert ctx.member is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await manage_connections_view(ctx.member, typing.cast(ConnectionKind, ctx.values[0]), game),
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
        assert ctx.member is not None

        await ctx.defer()
        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            **{f"{self.kind}_channel_id": next((c.id for c in ctx.channels), None)},
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await manage_connections_view(ctx.member, self.kind, game),
        )


class GameRoleSelect(flare.RoleSelect, placeholder="Select role", min_values=0, max_values=1):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None
        assert ctx.member is not None

        await ctx.defer()

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await plugin.model.create.remove_role(game)

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=ctx.guild_id,
            author_id=ctx.user.id,
            role_id=next((c.id for c in ctx.roles), None),
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await plugin.model.create.apply_role(game)

        await ctx.edit_response(
            **await manage_connections_view(ctx.member, "role", game),
        )


class AddPlayerSelect(flare.UserSelect, min_values=1, max_values=25, placeholder="Select Players to add"):
    game_id: int
    author_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int) -> typing.Self:
        return cls(game_id, author_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        await ctx.defer()

        await asyncio.gather(
            *[plugin.model.players.insert(user_id=user.id, game_id=self.game_id) for user in ctx.users]
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await plugin.model.create.apply_role(game)

        await ctx.edit_response(
            **await players_settings_view(game),
        )


class ManagePlayerSelect(flare.TextSelect, min_values=1, max_values=1, placeholder="Select Player to manage"):
    game_id: int
    author_id: int

    @classmethod
    async def make(cls, game: Game, selected: hikari.Snowflake | None) -> typing.Self:
        options: list[hikari.SelectMenuOption] = []
        for player in game.players:
            member = plugin.app.cache.get_member(game.guild_id, player.user_id) or await plugin.app.rest.fetch_member(
                game.guild_id, player.user_id
            )
            character = game.get_character_for(player)
            options.append(
                hikari.SelectMenuOption(
                    label=member.display_name,
                    value=str(player.user_id),
                    description=character.name if character is not None else None,
                    emoji=None,
                    is_default=player.user_id == selected,
                )
            )

        return cls(game.game_id, game.author_id).set_options(*options)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await manage_players_view(hikari.Snowflake(ctx.values[0]), game),
        )


class RemovePlayerButton(flare.Button, label="Remove Player", style=hikari.ButtonStyle.DANGER):
    game_id: int
    author_id: int
    player_id: int

    @classmethod
    def make(cls, game_id: int, author_id: int, player_id: int) -> typing.Self:
        return cls(game_id, author_id, player_id)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        await ctx.defer()

        await plugin.model.players.delete(game_id=self.game_id, user_id=self.player_id)

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await plugin.model.create.remove_role_from(game, hikari.Snowflake(self.player_id))

        await ctx.edit_response(
            **await manage_players_view(None, game),
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
            **await manage_details_view(game),
        )


class OverwritesButton(flare.Button, label="Apply Permissions", style=hikari.ButtonStyle.PRIMARY):
    game_id: int
    author_id: int
    kind: ConnectionKind

    @classmethod
    def make(cls, game_id: int, author_id: int, kind: ConnectionKind) -> typing.Self:
        return cls(game_id, author_id, kind)

    @only_author
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        match self.kind:
            case "main":
                channel_id = game.main_channel_id
            case "info":
                channel_id = game.info_channel_id
            case "synopsis":
                channel_id = game.synopsis_channel_id
            case "voice":
                channel_id = game.voice_channel_id
            case "category":
                channel_id = game.category_channel_id
            case "role":
                # we shouldn't get here
                raise ModronError("Can't apply permission overwrites to a role!")

        if channel_id is None:
            raise NotFoundError(f"{self.kind.capitalize()} Channel")

        await plugin.app.rest.edit_channel(channel_id, permission_overwrites=get_kind_overwrites(game, self.kind))

        response = await ctx.respond("✅ Successfully set permissions!", flags=hikari.MessageFlag.EPHEMERAL)
        await asyncio.sleep(5)
        await response.delete()


class ToggleSeekingPlayers(flare.Button, style=hikari.ButtonStyle.PRIMARY):
    game_id: int
    author_id: int
    seeking_players: bool

    @classmethod
    def make(cls, game_id: int, author_id: int, seeking_players: bool) -> typing.Self:
        return (
            cls(game_id, author_id, seeking_players)
            .set_label("Stop Seeking Players" if seeking_players else "Start Seeking Players")
            .set_emoji("⛔" if seeking_players else "🪧")
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

        await ctx.edit_response(**await players_settings_view(game))


class EditButton(flare.Button, label="Edit Text", style=hikari.ButtonStyle.PRIMARY, emoji="📄"):
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
        assert ctx.member is not None

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
            await plugin.model.create.full_setup(game_lite)

        game = await plugin.model.games.get(
            game_id=game_lite.game_id,
            guild_id=ctx.guild_id,
        )

        await plugin.model.create.apply_role(game)

        await ctx.respond(
            **await settings_view(ctx.member, game),
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

        await ctx.edit_response(**await manage_details_view(game))


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
        response = await ctx.respond(
            "Game successfully deleted!", embeds=[], components=[], flags=hikari.MessageFlag.EPHEMERAL
        )
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
@crescent.command(name="delete", description="delete a game")
class GameDelete:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_editable(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            game_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.games.id_exists(game_id=game_id, guild_id=ctx.guild_id, author_id=ctx.user.id):
                raise AutocompleteSelectError()

        await GameDeleteModal.make(game_id).send(ctx.interaction)


@plugin.include
@game.child
@crescent.command(name="settings", description="view the settings menu for a specific game")
class GameSettings:
    name = crescent.option(
        str,
        "the name of the game",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_editable(ctx, option),
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

        game = await plugin.model.games.get(game_id=game_id, guild_id=ctx.guild_id)

        await ctx.respond(
            **await settings_view(ctx.member, game),
            ephemeral=True,
        )
