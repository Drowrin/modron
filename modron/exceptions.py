import typing

import hikari


class ModronError(Exception):
    def __init__(self, message: str = "an unexpected error occurred") -> None:
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


class NotFoundError(ModronError):
    def __init__(self, model_name: str) -> None:
        super().__init__(f"{model_name} not found!")


class EditPermissionError(ModronError):
    def __init__(self, model_name: str) -> None:
        super().__init__(f"You do not have permission to edit this {model_name}!")
