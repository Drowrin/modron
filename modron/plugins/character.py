from __future__ import annotations

import typing

import crescent
import flare
import hikari

from modron.exceptions import AutocompleteSelectError
from modron.models import Character, Game
from modron.utils import GuildContext, ModronPlugin, Response

plugin = ModronPlugin()

character = crescent.Group(
    "character",
    "commands to create, edit, and manage your characters",
    dm_enabled=False,
)


async def character_settings_view(game: Game, character: Character) -> Response:
    return {
        "content": "",
        "embeds": [await plugin.model.render.character(game, character, description=True)],
        "components": [],
    }


character_name_text_input = flare.TextInput(
    label="Name",
    placeholder="The character's name",
    style=hikari.TextInputStyle.SHORT,
    max_length=60,
    required=True,
)

character_pronouns_text_input = flare.TextInput(
    label="Pronouns",
    placeholder="Pronouns the character uses",
    style=hikari.TextInputStyle.SHORT,
    max_length=40,
    required=False,
)

character_image_text_input = flare.TextInput(
    label="Image URL",
    placeholder="URL pointing to an image",
    style=hikari.TextInputStyle.SHORT,
    max_length=256,
    required=False,
)

character_brief_text_input = flare.TextInput(
    label="Brief",
    placeholder="A brief description of your character",
    style=hikari.TextInputStyle.PARAGRAPH,
    max_length=128,
    required=False,
)

character_description_text_input = flare.TextInput(
    label="Description",
    placeholder="An extended description of your character",
    style=hikari.TextInputStyle.PARAGRAPH,
    max_length=1024,
    required=False,
)


class CharacterCreateModal(flare.Modal, title="New Character"):
    game_id: int

    name: flare.TextInput = character_name_text_input
    pronouns: flare.TextInput = character_pronouns_text_input
    brief: flare.TextInput = character_brief_text_input
    description: flare.TextInput = character_description_text_input
    image: flare.TextInput = character_image_text_input

    @classmethod
    def make(cls, game_id: int) -> typing.Self:
        return cls(game_id)

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None
        assert ctx.member is not None

        await ctx.defer()

        character = await plugin.model.characters.insert(
            game_id=self.game_id,
            author_id=ctx.user.id,
            name=self.name.value,
            pronouns=self.pronouns.value,
            brief=self.brief.value or "",
            description=self.description.value or "",
            image=self.image.value,
        )

        game = await plugin.model.games.get(game_id=self.game_id, guild_id=ctx.guild_id)

        await ctx.respond(
            **await character_settings_view(game, character),
            flags=hikari.MessageFlag.EPHEMERAL,
        )


@plugin.include
@character.child
@crescent.command(name="create", description="create a character in a game")
class CharacterCreate:
    game = crescent.option(
        str,
        "the game to create a character in",
        autocomplete=lambda ctx, option: plugin.model.games.autocomplete_involved(ctx, option),
    )

    async def callback(self, ctx: GuildContext) -> None:
        try:
            game_id = int(self.game)
        except ValueError as err:
            raise AutocompleteSelectError() from err

        if not await plugin.model.games.id_exists(guild_id=ctx.guild_id, game_id=game_id):
            raise AutocompleteSelectError()
        if not await plugin.model.players.exists(game_id=game_id, user_id=ctx.user.id):
            raise AutocompleteSelectError()

        await ctx.defer(ephemeral=True)
