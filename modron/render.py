import itertools
import typing

import hikari

from modron.models import Character, Game, GameLite, Player, System, SystemLite


class Renderer:
    def __init__(
        self,
        command_ids: dict[str, hikari.Snowflake],
        client: hikari.api.RESTClient,
        cache: hikari.api.Cache | None = None,
    ) -> None:
        self.client = client
        self.cache = cache
        self.command_ids = command_ids

    async def get_member(self, guild_id: int, user_id: int) -> hikari.Member:
        if self.cache is not None and (member := self.cache.get_member(guild_id, user_id)) is not None:
            return member
        return await self.client.fetch_member(guild_id, user_id)

    def mention_command(self, name: str) -> str:
        return f"</{name}:{self.command_ids.get(name.split()[0], None)}>"

    async def system(self, system: SystemLite, *, description: bool = False) -> hikari.Embed:
        embed = (
            hikari.Embed(title=f"{system.emoji} {system.name}")
            .set_thumbnail(system.image)
            .add_field("Author Label", system.author_label, inline=True)
            .add_field("Player Label", system.player_label, inline=True)
        )

        if system.abbreviation != system.name:
            embed.description = f"Abbreviated as `{system.abbreviation}`"

        if description and system.description is not None:
            embed.add_field("Description", system.description)

        return embed

    async def system_games(self, system: System, *, start: int = 0, stop: int = 10) -> typing.Sequence[hikari.Embed]:
        return [
            hikari.Embed(
                title=game.name,
                timestamp=game.created_at,
                color=game.status.color,
            )
            .set_footer("Created")
            .set_thumbnail(game.image)
            .add_field("Status", game.status_str, inline=True)
            .add_field(
                "Seeking Players",
                "✅ Yes" if game.seeking_players else "⏹️ No",
                inline=True,
            )
            .add_field("More Details", self.mention_command("game info"), inline=True)
            for game in itertools.islice(system.games, start, stop)
        ]

    async def game(
        self,
        game: GameLite | Game,
        *,
        abbreviation: bool = False,
        description: bool = False,
        guild_resources: bool = False,
        full_image: bool = False,
        players: bool = False,
    ) -> hikari.Embed:
        embed = hikari.Embed(
            title=game.name,
            timestamp=game.created_at,
            color=game.status.color,
        ).set_footer("Created")

        if full_image:
            embed.set_image(game.image)
        else:
            embed.set_thumbnail(game.image)

        if abbreviation and game.abbreviation != game.name:
            embed.description = f"Abbreviated as `{game.abbreviation}`"

        if game.system is not None:
            embed.add_field("System", f"{game.system.emoji} {game.system.abbreviation}", inline=True)

        embed.add_field("Status", game.status_str, inline=True)
        embed.add_field(
            "Seeking Players",
            "✅ Yes" if game.seeking_players else "⏹️ No",
            inline=True,
        )

        if description and game.description is not None:
            embed.add_field("Description", game.description)

        if guild_resources:
            if game.main_channel_id is not None:
                embed.add_field("Main Channel", f"<#{game.main_channel_id}>", inline=True)

            if game.info_channel_id is not None:
                embed.add_field("Info Channel", f"<#{game.info_channel_id}>", inline=True)

            if game.synopsis_channel_id is not None:
                embed.add_field("Synopsis Channel", f"<#{game.synopsis_channel_id}>", inline=True)

            if game.voice_channel_id is not None:
                embed.add_field("Voice Channel", f"<#{game.voice_channel_id}>", inline=True)

            if game.role_id is not None:
                embed.add_field("Role", f"<@&{game.role_id}>", inline=True)

            if game.category_channel_id is not None:
                embed.add_field("Category", f"<#{game.category_channel_id}>", inline=True)

        if players and isinstance(game, Game) and len(game.players) > 0:
            embed.add_field(
                "Players",
                (
                    f"{game.author_label}: <@{game.author_id}>\n"
                    + f"{game.player_label}:"
                    + " ".join(f"<@{p.user_id}>" for p in game.players)
                ),
            )

        return embed

    async def game_author(self, game: GameLite) -> hikari.Embed:
        member = await self.get_member(game.guild_id, game.author_id)

        return hikari.Embed(title=game.author_label).set_author(
            name=member.display_name, icon=member.display_avatar_url
        )

    async def character(self, game: Game, character: Character, description: bool = False) -> hikari.Embed:
        embed = hikari.Embed(title=character.name)
        embed.set_thumbnail(character.image)
        if character.pronouns is not None:
            embed.add_field("Pronouns", character.pronouns, inline=True)
        if character.brief is not None:
            embed.add_field("Brief", character.brief)
        if description and character.description is not None:
            embed.add_field("Description", character.description)

        if (player := game.get_player_for(character)) is not None:
            member = await self.get_member(game.guild_id, player.user_id)
            embed.set_footer(game.player_label)
            embed.set_author(name=member.display_name, icon=member.display_avatar_url)

        return embed

    async def player(self, game: Game, player: Player) -> hikari.Embed:
        embed = hikari.Embed()

        member = await self.get_member(game.guild_id, player.user_id)
        embed.set_footer(game.player_label)
        embed.set_author(name=member.display_name, icon=member.display_avatar_url)

        if (character := game.get_character_for(player)) is not None:
            embed.title = character.name
            embed.set_thumbnail(character.image)
            if character.pronouns is not None:
                embed.add_field("Pronouns", character.pronouns, inline=True)
            if character.brief is not None:
                embed.add_field("Brief", character.brief)

        return embed
