import typing

from datetime import datetime
from enum import Enum


import attrs


class GameStatus(typing.NamedTuple("GameStatus", label=str, description=str, color=str, emoji=str), Enum):
    UNSTARTED = "Unstarted", "This game has not started having sessions yet", "DDDD11", "⏯️"
    RUNNING = "Running", "This game is having regular sessions", "11FF11", "▶️"
    PAUSED = "Paused", "This game is on hold temporarily", "1111FF", "⏸️"
    FINISHED = "Finished", "This game is completed and will not have future sessions", "AAAAAA", "⏹️"

    def __str__(self):
        self.description
        return self.name.lower()


@attrs.define
class Game:
    game_id: int
    name: str
    description: str
    system: str

    guild_id: int
    owner_id: int

    status: GameStatus = attrs.field(converter=lambda s: GameStatus[s.upper()])
    seeking_players: bool

    created_at: datetime

    image: str | None = None
    thumb: str | None = None

    category_id: int | None = None
    main_channel_id: int | None = None
    info_channel_id: int | None = None
    schedule_channel_id: int | None = None
    synopsis_channel_id: int | None = None

    @property
    def status_str(self) -> str:
        status = f"{self.status.emoji} {self.status.label}"

        if self.seeking_players:
            status += " - Seeking Players"

        return status
