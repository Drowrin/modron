import typing

import hikari


class ModronError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def to_response_args(self) -> dict[str, typing.Any]:
        return {
            "embed": hikari.Embed(title=self.message, color="FF1111"),
            "flags": hikari.MessageFlag.EPHEMERAL,
        }


class GameError(ModronError):
    def __init__(self, message: str, game_id: int) -> None:
        super().__init__(message)
        self.game_id = game_id


class GameNotFoundError(GameError):
    def __init__(self, game_id: int) -> None:
        super().__init__(f"Game with id {game_id} not found!", game_id)


class GamePermissionError(GameError):
    def __init__(self, game_id: int) -> None:
        super().__init__("You do not have permission to edit this game!", game_id)
