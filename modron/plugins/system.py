from __future__ import annotations

import asyncio
import datetime
import typing

import crescent
import flare
import hikari
import toolbox

from modron.exceptions import AutocompleteSelectError, ConfirmationError, EditPermissionError, NotUniqueError
from modron.models import SystemLite
from modron.utils import GuildContext, ModronPlugin, Response

MANAGE_SYSTEM_PERMISSIONS = hikari.Permissions.MANAGE_GUILD

plugin = ModronPlugin()
system = crescent.Group(
    "system",
    "system management",
    dm_enabled=False,
    default_member_permissions=MANAGE_SYSTEM_PERMISSIONS,
)

SignatureT = typing.Callable[[typing.Any, flare.MessageContext], typing.Coroutine[typing.Any, typing.Any, None]]


def require_permissions(f: SignatureT):
    async def inner(self: typing.Any, ctx: flare.MessageContext) -> None:
        assert ctx.member is not None

        permissions = toolbox.members.calculate_permissions(ctx.member)

        if (permissions & MANAGE_SYSTEM_PERMISSIONS) != MANAGE_SYSTEM_PERMISSIONS:
            raise EditPermissionError("System")

        return await f(self, ctx)

    return inner


async def settings_view(system: SystemLite) -> Response:
    return {
        "content": None,
        "embeds": await asyncio.gather(
            plugin.model.render.system(system, description=True),
        ),
        "components": await asyncio.gather(
            flare.Row(
                EmojiButton.make(system.system_id, 60),
                EditButton.make(system.system_id),
            ),
        ),
    }


async def emoji_settings_view(system_id: int, seconds: int) -> Response:
    timestamp = toolbox.strings.format_dt(
        toolbox.strings.utcnow() + datetime.timedelta(seconds=seconds), toolbox.strings.TimestampStyle.RELATIVE
    )
    return {
        "content": None,
        "embeds": [
            hikari.Embed(
                description=(
                    f"React to this message to set the Emoji for this system.\nThis process will cancel {timestamp}"
                )
            )
        ],
        "components": await asyncio.gather(
            flare.Row(
                CancelButton.make(),
            ),
        ),
    }


class CancelButton(flare.Button, label="Cancel"):
    @classmethod
    def make(cls) -> typing.Self:
        return cls()

    @require_permissions
    async def callback(self, ctx: flare.MessageContext) -> None:
        await ctx.message.delete()


class BackButton(flare.Button, label="Back"):
    system_id: int

    @classmethod
    def make(cls, system_id: int) -> typing.Self:
        return cls(system_id)

    @require_permissions
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        system = await plugin.model.systems.get(system_id=self.system_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(system),
        )


class EmojiButton(flare.Button, label="Set Emoji", emoji="🎨"):
    system_id: int
    timeout: int

    @classmethod
    def make(cls, system_id: int, timeout: int) -> typing.Self:
        return cls(system_id, timeout)

    @require_permissions
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        old_message = ctx.interaction.message

        response = await ctx.respond(**await emoji_settings_view(self.system_id, self.timeout))
        message = await response.retrieve_message()

        try:
            event = await plugin.app.wait_for(
                hikari.ReactionAddEvent,
                timeout=self.timeout,
                predicate=lambda e: e.message_id == message.id and e.user_id == ctx.user.id,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return
        finally:
            try:
                await response.delete()
            except (hikari.NotFoundError, hikari.ComponentStateConflictError):
                pass

        await plugin.model.systems.update(
            system_id=self.system_id,
            guild_id=ctx.guild_id,
            emoji_name=event.emoji_name,
            emoji_id=event.emoji_id,
            emoji_animated=event.is_animated,
        )

        system = await plugin.model.systems.get(system_id=self.system_id, guild_id=ctx.guild_id)

        await ctx.interaction.edit_message(old_message, **await settings_view(system))


class EditButton(flare.Button, label="Edit Details", emoji="📄"):
    system_id: int

    @classmethod
    def make(cls, system_id: int) -> typing.Self:
        return cls(system_id)

    @require_permissions
    async def callback(self, ctx: flare.MessageContext) -> None:
        assert ctx.guild_id is not None

        system = await plugin.model.systems.get_lite(system_id=self.system_id, guild_id=ctx.guild_id)

        await SystemEditModal.make(system).send(ctx.interaction)


system_name_text_input = flare.TextInput(
    label="Name",
    style=hikari.TextInputStyle.SHORT,
    max_length=30,
    required=True,
)

system_author_text_input = flare.TextInput(
    label="Author Label",
    placeholder="Author",
    style=hikari.TextInputStyle.SHORT,
    max_length=30,
    required=False,
)

system_player_text_input = flare.TextInput(
    label="Player Label",
    placeholder="Player",
    style=hikari.TextInputStyle.SHORT,
    max_length=30,
    required=False,
)

system_description_text_input = flare.TextInput(
    label="Description",
    style=hikari.TextInputStyle.PARAGRAPH,
    max_length=1024,
    required=False,
)

system_image_text_input = flare.TextInput(
    label="Image URL",
    style=hikari.TextInputStyle.SHORT,
    max_length=256,
    required=False,
)


class SystemCreateModal(flare.Modal, title="New System"):
    name: flare.TextInput = system_name_text_input
    author_label: flare.TextInput = system_author_text_input
    player_label: flare.TextInput = system_player_text_input
    description: flare.TextInput = system_description_text_input
    image: flare.TextInput = system_image_text_input

    @classmethod
    def make(
        cls,
        name: str,
        author_label: str | None = None,
        player_label: str | None = None,
        description: str | None = None,
        image: str | None = None,
    ) -> typing.Self:
        instance = cls()
        instance.name.set_value(name)
        instance.author_label.set_value(author_label)
        instance.player_label.set_value(player_label)
        instance.description.set_value(description)
        instance.image.set_value(image)
        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.author_label.value is not None
        assert self.player_label.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        system = await plugin.model.systems.insert(
            guild_id=ctx.guild_id,
            name=self.name.value,
            # replace '' with None
            author_label=self.author_label.value,
            player_label=self.player_label.value,
            description=self.description.value or None,
            image=self.image.value or None,
        )

        await ctx.respond(
            **await settings_view(system),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class SystemEditModal(flare.Modal, title="Edit System"):
    system_id: int

    name: flare.TextInput = system_name_text_input
    author_label: flare.TextInput = system_author_text_input
    player_label: flare.TextInput = system_player_text_input
    description: flare.TextInput = system_description_text_input
    image: flare.TextInput = system_image_text_input

    @classmethod
    def make(cls, system: SystemLite) -> typing.Self:
        instance = cls(system.system_id)
        instance.name.set_value(system.name)
        instance.author_label.set_value(system.author_label)
        instance.player_label.set_value(system.player_label)
        instance.description.set_value(system.description)
        instance.image.set_value(system.image)
        return instance

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.author_label.value is not None
        assert self.player_label.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None

        await ctx.defer()

        await plugin.model.systems.update(
            system_id=self.system_id,
            guild_id=ctx.guild_id,
            name=self.name.value,
            author_label=self.author_label.value,
            player_label=self.player_label.value,
            # replace '' with None
            description=self.description.value or None,
            image=self.image.value or None,
        )
        system = await plugin.model.systems.get_lite(system_id=self.system_id, guild_id=ctx.guild_id)

        await ctx.edit_response(
            **await settings_view(system),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


class SystemDeleteModal(flare.Modal, title="System Delete Confirmation"):
    system_id: int

    confirmation: flare.TextInput = flare.TextInput(
        label='Please confirm by typing "CONFIRM" in caps',
        placeholder="This can not be undone",
        style=hikari.TextInputStyle.SHORT,
        required=True,
    )

    @classmethod
    def make(cls, system_id: int) -> typing.Self:
        return cls(system_id)

    async def callback(self, ctx: flare.ModalContext) -> None:
        if self.confirmation.value != "CONFIRM":
            raise ConfirmationError()

        await plugin.model.systems.delete(system_id=self.system_id)
        response = await ctx.respond(
            "System successfully deleted!", embeds=[], components=[], flags=hikari.MessageFlag.EPHEMERAL
        )
        await asyncio.sleep(5)
        await response.delete()


@plugin.include
@system.child
@crescent.command(name="create", description="create a new system in this server")
class SystemCreate:
    name = crescent.option(
        str,
        "The name this system will have (can be changed later)",
        max_length=30,
    )

    async def callback(self, ctx: GuildContext) -> None:
        assert ctx.guild_id is not None

        if await plugin.model.systems.name_exists(name=self.name, guild_id=ctx.guild_id):
            raise NotUniqueError("System", name=self.name)

        await SystemCreateModal.make(name=self.name).send(ctx.interaction)


@plugin.include
@system.child
@crescent.command(name="delete", description="delete a system")
class SystemDelete:
    name = crescent.option(
        str,
        "the name of the system",
        autocomplete=lambda ctx, option: plugin.model.systems.autocomplete(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            system_id = int(self.name)
        except ValueError as err:
            raise AutocompleteSelectError() from err
        else:
            if not await plugin.model.systems.id_exists(system_id=system_id, guild_id=ctx.guild_id):
                raise AutocompleteSelectError()

        await SystemDeleteModal.make(system_id).send(ctx.interaction)


@plugin.include
@system.child
@crescent.command(name="settings", description="view the settings menu for a specific system")
class SystemSettings:
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

        await ctx.defer(ephemeral=True)

        system = await plugin.model.systems.get_lite(system_id=system_id, guild_id=ctx.guild_id)

        await ctx.respond(
            **await settings_view(system),
            ephemeral=True,
        )
