import typing

import hikari


class ModronError(Exception):
    def __init__(self, message: str = "an unexpected error occurred") -> None:
        super().__init__()
        self.message = message

    def embed(self) -> hikari.Embed:
        return hikari.Embed(title=self.message, color="FF1111")

    def to_response_args(self) -> dict[str, typing.Any]:
        return {
            "embed": self.embed(),
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


class AutocompleteSelectError(ModronError):
    def __init__(self) -> None:
        super().__init__("Please select an autocomplete suggestion!")


class NotUniqueError(ModronError):
    def __init__(self, model_name: str, **kwargs: typing.Any) -> None:
        super().__init__(f"Too similar to an existing {model_name}!")
        self.extras = kwargs

    def embed(self) -> hikari.Embed:
        embed = super().embed()
        for k, v in self.extras.items():
            embed.add_field(k, str(v))
        return embed
