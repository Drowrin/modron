import crescent
import flare
import hikari
import datetime

from modron.app import ModronApp, ModronPlugin

plugin = ModronPlugin()
game = crescent.Group(
    "game",
    "game management",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.MANAGE_MESSAGES,
)

STATUS_COLORS = {
    "unstarted": "DDDD11",
    "running": "11FF11",
    "paused": "1111FF",
    "finished": "AAAAAA",
}


async def create_game_menu(app: ModronApp, game_id: int) -> tuple[hikari.Embed, flare.Row | None]:
    game = await app.db.fetchrow("SELECT * from Games WHERE id = $1;", game_id)

    if game is None:
        # an error message
        return (hikari.Embed(title=f"Game with id {game_id} not found!", color="FF1111"), None)

    embed = hikari.Embed(
        title=game["name"],
        description=game["description"],
        # hikari will check the timezone, so we need to explicitly set this to utc
        timestamp=game['created_at'].replace(tzinfo=datetime.timezone.utc),
        color=STATUS_COLORS.get(
            game["status"],
            "DDDDDD",  # unknown status color for some reason? might be better to error here and figure out why?
        ),
    ).set_footer(f"Status: {game['status']}")

    # row = await flare.Row()

    return embed, None


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

        await ctx.defer()

        game_id = await ctx.app.db.insert_game(
            name=self.name.value,
            description=self.description.value,
            system=self.system,
            guild_id=ctx.guild_id,
            owner_id=ctx.user.id,
        )

        embed, row = await create_game_menu(ctx.app, game_id)

        await ctx.respond(
            f"You can view this menu again with </game create:{ctx.interaction.}>",
            embed=embed,
            component=row or hikari.UNDEFINED,
        )


async def autocomplete_systems(
    ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption
) -> list[hikari.CommandChoice]:
    assert isinstance(ctx.app, ModronApp)

    results = await ctx.app.db.fetch(
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
        await GameCreateModal(self.system).set_title(f"New {self.system} Game").send(ctx.interaction)


async def autocomplete_games(ctx: crescent.AutocompleteContext, option: hikari.AutocompleteInteractionOption) -> list[hikari.CommandChoice]:
    assert isinstance(ctx.app, ModronApp)
    
    results = await ctx.app.db.fetch(
        "SELECT id, name FROM Games WHERE guild_id = $1 AND name LIKE $2 LIMIT 25;",
        ctx.guild_id,
        f"{option.value}%",
    )

    return [hikari.CommandChoice(name=r['name'], value=str(r['id'])) for r in results]


@plugin.include
@game.child
@crescent.command(name="menu", description="view the menu for a specific game")
class GameMenu:
    name = crescent.option(
        str, "the name of the game", autocomplete=autocomplete_games
    )
    
    async def callback(self, ctx: crescent.Context) -> None:
        assert isinstance(ctx.app, ModronApp)
        
        try:
            game_id = int(self.name)
        except ValueError:
            await ctx.respond(
                'Please select an autocomplete suggestion',
                flags=hikari.MessageFlag.EPHEMERAL,
            )
        else:
            embed, row = await create_game_menu(ctx.app, game_id)
            
            await ctx.respond(
                embed=embed,
                component=row or hikari.UNDEFINED,
            )
