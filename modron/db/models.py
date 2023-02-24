from __future__ import annotations

import typing
from datetime import datetime
from enum import Enum

import attrs


@attrs.define(kw_only=True)
class SystemLite:
    system_id: int

    guild_id: int

    name: str
    description: str | None = None

    author_label: str
    player_label: str

    image: str | None = None


@attrs.define(kw_only=True)
class System(SystemLite):
    games: list[GameLite] = attrs.field(converter=lambda rs: [GameLite(**r) for r in rs])


class GameStatus(typing.NamedTuple("GameStatus", label=str, description=str, color=str, emoji=str), Enum):
    UNSTARTED = "Unstarted", "This game has not started having sessions yet", "DDDD11", "⏯️"
    RUNNING = "Running", "This game is having regular sessions", "11FF11", "▶️"
    PAUSED = "Paused", "This game is on hold temporarily", "1111FF", "⏸️"
    FINISHED = "Finished", "This game is completed and will not have future sessions", "AAAAAA", "⏹️"

    def __str__(self):
        self.description
        return self.name.lower()


@attrs.define(kw_only=True)
class GameLite:
    game_id: int

    system_id: int | None = None

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


@attrs.define(kw_only=True)
class Game(GameLite):
    system: SystemLite | None = attrs.field(converter=lambda rs: next((SystemLite(**r) for r in rs), None))
    characters: list[Character] = attrs.field(converter=lambda rs: [Character(**r) for r in rs])
    players: list[Player] = attrs.field(converter=lambda rs: [Player(**r) for r in rs])


@attrs.define(kw_only=True)
class Character:
    character_id: int
    game_id: int
    author_id: int

    name: str

    brief: str
    description: str

    pronouns: str | None = None

    image: str | None = None


@attrs.define(kw_only=True)
class Player:
    user_id: int
    game_id: int

    character_id: int | None = None

    def get_character_in(self, game: Game) -> Character | None:
        return next((c for c in game.characters if c.character_id == self.character_id), None)
