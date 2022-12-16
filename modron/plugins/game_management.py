import crescent
import flare
import hikari

from modron.app import ModronApp, ModronPlugin

plugin = ModronPlugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.MANAGE_MESSAGES,
)


class GameCreateModal(flare.Modal, title="Create a new game!"):
    system: str

    name: flare.TextInput = flare.TextInput(
        label="Title",
        style=hikari.TextInputStyle.SHORT,
        min_length=1,
        max_length=100,
        required=True,
    )

    description: flare.TextInput = flare.TextInput(
        label="Description",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=1,
        max_length=4000,
        required=True,
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required, so they should not be None
        assert self.name.value is not None
        assert self.description.value is not None
        # this can only be accessed in guilds, so this should not be None
        assert ctx.guild_id is not None
        # assert the bot type
        assert isinstance(ctx.app, ModronApp)

        await ctx.app.db.insert_game(
            name=self.name.value,
            description=self.description.value,
            system=self.system,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
        )

        # TODO: display game (menu?), make posts/channels, etc.
        await ctx.respond("success!", flags=hikari.MessageFlag.EPHEMERAL)


async def autocomplete_systems(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    assert isinstance(ctx.app, ModronApp)

    results = await ctx.app.db.fetch(
        "SELECT DISTINCT system FROM Games WHERE guild_id = $1 AND system LIKE $2",
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
        await GameCreateModal(self.system).set_title(f"New {self.system} Game").send(ctx.interaction)
