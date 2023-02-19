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


class ConfirmationError(ModronError):
    def __init__(self) -> None:
        super().__init__("Confirmation input did not match!")


class GameNotFoundError(ModronError):
    def __init__(self, game_id: int) -> None:
        super().__init__(f"Game with id {game_id} not found!")


class GamePermissionError(ModronError):
    def __init__(self, game_id: int) -> None:
        super().__init__("You do not have permission to edit this game!")
