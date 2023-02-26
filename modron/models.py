from __future__ import annotations

import itertools
import typing
from datetime import datetime
from enum import Enum

import attrs
import crescent
import hikari

if typing.TYPE_CHECKING:
    from modron.model import Model

    Plugin = crescent.Plugin[hikari.GatewayBot, Model]
else:
    Plugin = crescent.Plugin[hikari.GatewayBot, None]

plugin = Plugin()


class Response(typing.TypedDict):
    content: hikari.UndefinedNoneOr[str]
    embeds: typing.Sequence[hikari.Embed]
    components: typing.Sequence[hikari.api.ComponentBuilder]


async def get_member(guild_id: int, user_id: int) -> hikari.Member:
    return plugin.app.cache.get_member(guild_id, user_id) or await plugin.app.rest.fetch_member(guild_id, user_id)


@attrs.define(kw_only=True)
class SystemLite:
    system_id: int

    guild_id: int

    name: str
    description: str | None = None

    author_label: str
    player_label: str

    image: str | None = None

    async def embed(self, *, description: bool = False) -> hikari.Embed:
        embed = (
            hikari.Embed(
                title=self.name,
            )
            .set_thumbnail(self.image)
            .add_field("Author Label", self.author_label, inline=True)
            .add_field("Player Label", self.player_label, inline=True)
        )

        if description and self.description is not None:
            embed.add_field("Description", self.description)

        return embed


@attrs.define(kw_only=True)
class System(SystemLite):
    games: list[GameLite] = attrs.field(converter=lambda rs: [GameLite(**r) for r in rs])

    async def game_embeds(self, *, start: int = 0, stop: int = 10) -> typing.Sequence[hikari.Embed]:
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
            .add_field("More Details", plugin.model.mention_command("game info"), inline=True)
            for game in itertools.islice(self.games, start, stop)
        ]

    def __attrs_post_init__(self) -> None:
        for g in self.games:
            object.__setattr__(g, "system", self)


class GameStatus(typing.NamedTuple("GameStatus", label=str, description=str, color=str, emoji=str), Enum):
    UNSTARTED = "Unstarted", "This game has not started having sessions yet", "DDDD11", "⏯️"
    RUNNING = "Running", "This game is having regular sessions", "11FF11", "▶️"
    PAUSED = "Paused", "This game is on hold temporarily", "1111FF", "⏸️"
    FINISHED = "Finished", "This game is completed and will not have future sessions", "AAAAAA", "⏹️"

    def __str__(self):
        self.description
        return self.name.lower()


def system_converter(rs: list[dict[str, typing.Any]] | SystemLite | None):
    if rs is None:
        return None
    if isinstance(rs, SystemLite):
        return rs
    return next((SystemLite(**r) for r in rs), None)


@attrs.define(kw_only=True)
class GameLite:
    game_id: int

    system_id: int | None = None
    system: SystemLite | None = attrs.field(converter=system_converter, default=None)

    guild_id: int
    owner_id: int

    name: str
    abbreviation: str
    description: str | None = None
    image: str | None = None

    status: GameStatus = attrs.field(converter=lambda s: GameStatus[s.upper()])
    seeking_players: bool

    created_at: datetime

    role_id: int | None = None

    category_channel_id: int | None = None
    main_channel_id: int | None = None
    info_channel_id: int | None = None
    synopsis_channel_id: int | None = None
    voice_channel_id: int | None = None

    @property
    def status_str(self) -> str:
        status = f"{self.status.emoji} {self.status.label}"

        return status

    @property
    def system_name(self) -> str | None:
        if self.system is None:
            return None
        return self.system.name

    @property
    def author_label(self) -> str:
        if self.system is None:
            return "Author"
        return self.system.author_label

    @property
    def player_label(self) -> str:
        if self.system is None:
            return "Player"
        return self.system.player_label

    async def embed(
        self, *, abbreviation: bool = False, description: bool = False, guild_resources: bool = False
    ) -> hikari.Embed:
        embed = (
            hikari.Embed(
                title=self.name,
                timestamp=self.created_at,
                color=self.status.color,
            )
            .set_footer("Created")
            .set_thumbnail(self.image)
        )

        if abbreviation:
            embed.description = f"Abbreviated as `{self.abbreviation}`"

        if (system_name := self.system_name) is not None:
            embed.add_field("System", system_name, inline=True)

        embed.add_field("Status", self.status_str, inline=True)
        embed.add_field(
            "Seeking Players",
            "✅ Yes" if self.seeking_players else "⏹️ No",
            inline=True,
        )

        if description and self.description is not None:
            embed.add_field("Description", self.description)

        if guild_resources:
            if self.main_channel_id is not None:
                embed.add_field("Main Channel", f"<#{self.main_channel_id}>", inline=True)

            if self.info_channel_id is not None:
                embed.add_field("Info Channel", f"<#{self.info_channel_id}>", inline=True)

            if self.synopsis_channel_id is not None:
                embed.add_field("Synopsis Channel", f"<#{self.synopsis_channel_id}>", inline=True)

            if self.voice_channel_id is not None:
                embed.add_field("Voice Channel", f"<#{self.voice_channel_id}>", inline=True)

            if self.category_channel_id is not None:
                embed.add_field("Category", f"<#{self.category_channel_id}>", inline=True)

            if self.role_id is not None:
                embed.add_field("Role", f"<@&{self.role_id}>", inline=True)

        return embed

    async def author_embed(self) -> hikari.Embed:
        member = await get_member(self.guild_id, self.owner_id)

        return hikari.Embed(title=self.author_label).set_author(
            name=member.display_name, icon=member.display_avatar_url
        )


@attrs.define(kw_only=True)
class Game(GameLite):
    characters: list[Character] = attrs.field(converter=lambda rs: [Character(**r) for r in rs])
    players: list[Player] = attrs.field(converter=lambda rs: [Player(**r) for r in rs])

    def get_character_for(self, player: Player) -> Character | None:
        return next((c for c in self.characters if c.character_id == player.character_id), None)

    def get_player_for(self, character: Character) -> Player | None:
        return next((p for p in self.players if p.character_id == character.character_id), None)

    async def embed(
        self,
        *,
        abbreviation: bool = False,
        description: bool = False,
        guild_resources: bool = False,
        players: bool = False,
    ) -> hikari.Embed:
        embed = await super().embed(abbreviation=abbreviation, description=description, guild_resources=guild_resources)

        if players and len(self.players) > 0:
            embed.add_field("Players", " ".join(f"<@{p.user_id}>" for p in self.players))

        return embed


@attrs.define(kw_only=True)
class Character:
    character_id: int
    game_id: int
    author_id: int

    name: str

    brief: str | None
    description: str | None

    pronouns: str | None = None

    image: str | None = None

    async def add_details_to(self, game: Game, embed: hikari.Embed, description: bool = False) -> hikari.Embed:
        embed.title = self.name
        embed.set_thumbnail(self.image)
        if self.pronouns is not None:
            embed.add_field("Pronouns", self.pronouns, inline=True)
        if self.brief is not None:
            embed.add_field("Brief", self.brief)
        if description and self.description is not None:
            embed.add_field("Description", self.description)
        return embed

    async def embed(self, game: Game, description: bool = False) -> hikari.Embed:
        embed = await self.add_details_to(game, hikari.Embed(), description)

        if (player := game.get_player_for(self)) is not None:
            embed = await player.add_details_to(game, embed)

        return embed


@attrs.define(kw_only=True)
class Player:
    user_id: int
    game_id: int

    character_id: int | None = None

    async def add_details_to(self, game: Game, embed: hikari.Embed) -> hikari.Embed:
        member = await get_member(game.guild_id, self.user_id)

        embed.set_footer(game.player_label)
        embed.set_author(name=member.display_name, icon=member.display_avatar_url)

        return embed

    async def embed(self, game: Game) -> hikari.Embed:
        embed = await self.add_details_to(game, hikari.Embed())

        if (character := game.get_character_for(self)) is not None:
            embed = await character.add_details_to(game, embed)

        return embed
