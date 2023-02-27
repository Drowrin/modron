from __future__ import annotations

import asyncio
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

    guild_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)

    name: str
    abbreviation: str
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

        if self.abbreviation != self.name:
            embed.description = f"Abbreviated as `{self.abbreviation}`"

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


def snowflake_or_none_converter(value: int | None) -> hikari.Snowflake | None:
    if value is None:
        return None
    return hikari.Snowflake(value)


@attrs.define(kw_only=True)
class GameLite:
    game_id: int

    system_id: int | None = None
    system: SystemLite | None = attrs.field(converter=system_converter, default=None)

    guild_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)
    author_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)

    name: str
    abbreviation: str = attrs.field()
    description: str | None = None
    image: str | None = None

    status: GameStatus = attrs.field(converter=lambda s: GameStatus[s.upper()])
    seeking_players: bool

    created_at: datetime

    role_id: hikari.Snowflake | None = attrs.field(converter=snowflake_or_none_converter)

    category_channel_id: int | None = attrs.field(converter=snowflake_or_none_converter)
    main_channel_id: int | None = attrs.field(converter=snowflake_or_none_converter)
    info_channel_id: int | None = attrs.field(converter=snowflake_or_none_converter)
    synopsis_channel_id: int | None = attrs.field(converter=snowflake_or_none_converter)
    voice_channel_id: int | None = attrs.field(converter=snowflake_or_none_converter)

    @abbreviation.default  # type: ignore
    def _default_abbreviation(self) -> str:
        return self.name[:25]

    @property
    def status_str(self) -> str:
        status = f"{self.status.emoji} {self.status.label}"

        return status

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
        self,
        *,
        abbreviation: bool = False,
        description: bool = False,
        guild_resources: bool = False,
        full_image: bool = False,
    ) -> hikari.Embed:
        embed = hikari.Embed(
            title=self.name,
            timestamp=self.created_at,
            color=self.status.color,
        ).set_footer("Created")

        if full_image:
            embed.set_image(self.image)
        else:
            embed.set_thumbnail(self.image)

        if abbreviation and self.abbreviation != self.name:
            embed.description = f"Abbreviated as `{self.abbreviation}`"

        if self.system is not None:
            embed.add_field("System", self.system.abbreviation, inline=True)

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

            if self.role_id is not None:
                embed.add_field("Role", f"<@&{self.role_id}>", inline=True)

            if self.category_channel_id is not None:
                embed.add_field("Category", f"<#{self.category_channel_id}>", inline=True)

        return embed

    async def author_embed(self) -> hikari.Embed:
        member = await get_member(self.guild_id, self.author_id)

        return hikari.Embed(title=self.author_label).set_author(
            name=member.display_name, icon=member.display_avatar_url
        )

    def category_overwrites(self) -> list[hikari.PermissionOverwrite]:
        perms = (
            hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.SEND_MESSAGES | hikari.Permissions.MANAGE_MESSAGES
        )
        return [
            hikari.PermissionOverwrite(
                id=self.author_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
            hikari.PermissionOverwrite(
                id=plugin.model.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
        ]

    def read_only_overwrites(self):
        perms = (
            hikari.Permissions.SEND_MESSAGES
            | hikari.Permissions.CREATE_PUBLIC_THREADS
            | hikari.Permissions.CREATE_PRIVATE_THREADS
            | hikari.Permissions.ADD_REACTIONS
        )
        return [
            hikari.PermissionOverwrite(
                id=self.guild_id,  # @everyone
                type=hikari.PermissionOverwriteType.ROLE,
                deny=perms,
            ),
            hikari.PermissionOverwrite(
                id=self.author_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
            hikari.PermissionOverwrite(
                id=plugin.model.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
        ]

    def voice_overwrites(
        self, role_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> list[hikari.PermissionOverwrite]:
        if role_id is hikari.UNDEFINED:
            return []

        return [
            hikari.PermissionOverwrite(
                id=self.guild_id,  # @everyone
                type=hikari.PermissionOverwriteType.ROLE,
                deny=hikari.Permissions.CONNECT,
            ),
            hikari.PermissionOverwrite(
                id=role_id,
                type=hikari.PermissionOverwriteType.ROLE,
                allow=hikari.Permissions.CONNECT,
            ),
            hikari.PermissionOverwrite(
                id=plugin.model.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=hikari.Permissions.CONNECT,
            ),
        ]

    async def create_role(self) -> hikari.Role:
        role = await plugin.app.rest.create_role(
            self.guild_id,
            name=self.abbreviation,
            mentionable=True,
        )
        await plugin.app.rest.add_role_to_member(
            self.guild_id,
            self.author_id,
            role.id,
        )
        return role

    async def create_channel_category(self) -> hikari.GuildCategory:
        return await plugin.app.rest.create_guild_category(
            self.guild_id,
            self.abbreviation,
            permission_overwrites=self.category_overwrites(),
        )

    async def create_channel(
        self, name: str, category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> hikari.GuildTextChannel:
        return await plugin.app.rest.create_guild_text_channel(
            self.guild_id,
            name=name,
            category=category_id,
        )

    async def create_read_only_channel(
        self, name: str, category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> hikari.GuildTextChannel:
        return await plugin.app.rest.create_guild_text_channel(
            self.guild_id, name=name, category=category_id, permission_overwrites=self.read_only_overwrites()
        )

    async def create_voice_channel(
        self,
        name: str,
        role_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
        category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
    ) -> hikari.GuildVoiceChannel:
        return await plugin.app.rest.create_guild_voice_channel(
            self.guild_id,
            name=name,
            category=category_id,
            permission_overwrites=self.voice_overwrites(role_id),
        )

    async def full_setup(self) -> None:
        category, role = await asyncio.gather(
            self.create_channel_category(),
            self.create_role(),
        )

        main, info, synopsis, voice = await asyncio.gather(
            self.create_channel("main", category.id),
            self.create_read_only_channel("info", category.id),
            self.create_read_only_channel("synopsis", category.id),
            self.create_voice_channel("Voice", role.id, category.id),
        )

        await plugin.model.games.update(
            game_id=self.game_id,
            guild_id=self.guild_id,
            author_id=self.author_id,
            role_id=role.id,
            category_channel_id=category.id,
            main_channel_id=main.id,
            info_channel_id=info.id,
            synopsis_channel_id=synopsis.id,
            voice_channel_id=voice.id,
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
        full_image: bool = False,
        players: bool = False,
    ) -> hikari.Embed:
        embed = await super().embed(
            abbreviation=abbreviation, description=description, guild_resources=guild_resources, full_image=full_image
        )

        if players and len(self.players) > 0:
            embed.add_field("Players", " ".join(f"<@{p.user_id}>" for p in self.players))

        return embed


@attrs.define(kw_only=True)
class Character:
    character_id: int
    game_id: int
    author_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)

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
    user_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)
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
