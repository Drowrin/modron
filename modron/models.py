from __future__ import annotations

import typing
from datetime import datetime
from enum import Enum

import attrs
import hikari


def snowflake_or_none_converter(value: int | None) -> hikari.Snowflake | None:
    if value is None:
        return None
    return hikari.Snowflake(value)


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

    emoji_name: str | None
    emoji_id: hikari.Snowflake | None = attrs.field(converter=snowflake_or_none_converter)
    emoji_animated: bool

    @property
    def emoji(self) -> hikari.Emoji | None:
        if self.emoji_name is None:
            return None

        if self.emoji_id is None:
            return hikari.UnicodeEmoji(self.emoji_name)

        return hikari.CustomEmoji(id=self.emoji_id, name=self.emoji_name, is_animated=self.emoji_animated)


@attrs.define(kw_only=True)
class System(SystemLite):
    games: list[GameLite] = attrs.field(converter=lambda rs: [GameLite(**r) for r in rs])

    def __attrs_post_init__(self) -> None:
        for g in self.games:
            object.__setattr__(g, "system", self)


class GameStatus(typing.NamedTuple("GameStatus", label=str, description=str, color=str, emoji=str), Enum):
    UNSTARTED = "Unstarted", "This game has not started having sessions yet", "DDDD11", "⏯️"
    RUNNING = "Running", "This game is having regular sessions", "11FF11", "▶️"
    PAUSED = "Paused", "This game is on hold temporarily", "1111FF", "⏸️"
    FINISHED = "Finished", "This game is completed and will not have future sessions", "AAAAAA", "⏹️"

    def __str__(self):
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


@attrs.define(kw_only=True)
class Game(GameLite):
    characters: list[Character] = attrs.field(converter=lambda rs: [Character(**r) for r in rs])
    players: list[Player] = attrs.field(converter=lambda rs: [Player(**r) for r in rs])

    def get_character_for(self, player: Player) -> Character | None:
        return next((c for c in self.characters if c.character_id == player.character_id), None)

    def get_player_for(self, character: Character) -> Player | None:
        return next((p for p in self.players if p.character_id == character.character_id), None)


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


@attrs.define(kw_only=True)
class Player:
    user_id: hikari.Snowflake = attrs.field(converter=hikari.Snowflake)
    game_id: int

    character_id: int | None = None
