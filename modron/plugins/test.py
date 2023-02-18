import hikari

from modron.model import ModronPlugin

plugin = ModronPlugin()


@plugin.load_hook
def add_startup_listener() -> None:
    plugin.app.subscribe(hikari.StartedEvent, callback=test_startup)


async def test_startup(_: hikari.Event):
    await plugin.model.games.insert(
        name="Dummy",
        description="L",
        system="L",
        guild_id=1049383163199230042,
        owner_id=81149671447207936,
    )
    game = await plugin.model.games.insert(
        name="Test Game",
        description="Test Description",
        system="D&D 5e",
        guild_id=1049383163199230042,
        owner_id=81149671447207936,
    )
    character_id: int = await plugin.model.characters.insert(
        game_id=game.game_id,
        author_id=81149671447207936,
        name="Sample Character",
        brief="Brief Description",
        description="Lorem Ipsum Long Description Text ETC",
    )
    await plugin.model.players.insert(
        user_id=81149671447207936,
        game_id=game.game_id,
        role="GM",
        character_id=character_id,
    )
    print(await plugin.model.db.fetch("SELECT * from Games;"))
    print(await plugin.model.db.fetch("SELECT * from Characters;"))
    print(await plugin.model.db.fetch("SELECT * from Players;"))
    print(await plugin.model.games.get(game.game_id, 1049383163199230042))
