from __future__ import annotations

import typing
from datetime import datetime
from enum import Enum

import attrs
import hikari

from modron.db.conn import Record


def snowflake_or_none_converter(value: int | None) -> hikari.Snowflake | None:
    if value is None:
        return None
    return hikari.Snowflake(value)

def snowflake_converter(snowflake: int) -> hikari.Snowflake:
    return hikari.Snowflake(snowflake)


@attrs.define(kw_only=True)
class SystemLite:
    system_id: int

    guild_id: hikari.Snowflake = attrs.field(converter=snowflake_converter)

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


def games_converter(rs: list[Record]) -> list[GameLite]:
    return [GameLite(**r) for r in rs]


@attrs.define(kw_only=True)
class System(SystemLite):
    games: list[GameLite] = attrs.field(converter=games_converter)

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


def game_status_converter(s: str) -> GameStatus:
    return GameStatus[s.upper()]


@attrs.define(kw_only=True)
class GameLite:
    game_id: int

    system_id: int | None = None
    system: SystemLite | None = attrs.field(converter=system_converter, default=None)

    guild_id: hikari.Snowflake = attrs.field(converter=snowflake_converter)
    author_id: hikari.Snowflake = attrs.field(converter=snowflake_converter)

    name: str
    abbreviation: str = attrs.field()
    description: str | None = None
    image: str | None = None

    status: GameStatus = attrs.field(converter=game_status_converter)
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


def characters_converter(rs: list[Record]) -> list[Character]:
    return [Character(**r) for r in rs]


def players_converter(rs: list[Record]) -> list[Player]:
    return [Player(**r) for r in rs]


@attrs.define(kw_only=True)
class Game(GameLite):
    characters: list[Character] = attrs.field(converter=characters_converter)
    players: list[Player] = attrs.field(converter=players_converter)

    def get_character_for(self, player: Player) -> Character | None:
        return next((c for c in self.characters if c.character_id == player.character_id), None)

    def get_player_for(self, character: Character) -> Player | None:
        return next((p for p in self.players if p.character_id == character.character_id), None)


@attrs.define(kw_only=True)
class Character:
    character_id: int
    game_id: int
    author_id: hikari.Snowflake = attrs.field(converter=snowflake_converter)

    name: str

    brief: str | None
    description: str | None

    pronouns: str | None = None

    image: str | None = None


@attrs.define(kw_only=True)
class Player:
    user_id: hikari.Snowflake = attrs.field(converter=snowflake_converter)
    game_id: int

    character_id: int | None = None
