import asyncio
import typing

import hikari

from modron.db.games import GameDB
from modron.models import Game, GameLite


class Fabricator:
    def __init__(self, app_id: hikari.Snowflake, games: GameDB, client: hikari.api.RESTClient) -> None:
        self.app_id = app_id
        self.client = client
        self.games = games

    def category_overwrites(self, game: GameLite) -> list[hikari.PermissionOverwrite]:
        perms = (
            hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.SEND_MESSAGES | hikari.Permissions.MANAGE_MESSAGES
        )
        return [
            hikari.PermissionOverwrite(
                id=game.author_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
            hikari.PermissionOverwrite(
                id=self.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
        ]

    def read_only_overwrites(self, game: GameLite) -> typing.Sequence[hikari.PermissionOverwrite]:
        perms = (
            hikari.Permissions.SEND_MESSAGES
            | hikari.Permissions.CREATE_PUBLIC_THREADS
            | hikari.Permissions.CREATE_PRIVATE_THREADS
            | hikari.Permissions.ADD_REACTIONS
        )
        return [
            hikari.PermissionOverwrite(
                id=game.guild_id,  # @everyone
                type=hikari.PermissionOverwriteType.ROLE,
                deny=perms,
            ),
            hikari.PermissionOverwrite(
                id=game.author_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
            hikari.PermissionOverwrite(
                id=self.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=perms,
            ),
        ]

    def voice_overwrites(
        self, game: GameLite, role_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> list[hikari.PermissionOverwrite]:
        if role_id is hikari.UNDEFINED:
            if game.role_id is None:
                return []

            role_id = game.role_id

        return [
            hikari.PermissionOverwrite(
                id=game.guild_id,  # @everyone
                type=hikari.PermissionOverwriteType.ROLE,
                deny=hikari.Permissions.CONNECT,
            ),
            hikari.PermissionOverwrite(
                id=role_id,
                type=hikari.PermissionOverwriteType.ROLE,
                allow=hikari.Permissions.CONNECT,
            ),
            hikari.PermissionOverwrite(
                id=self.app_id,
                type=hikari.PermissionOverwriteType.MEMBER,
                allow=hikari.Permissions.CONNECT,
            ),
        ]

    async def remove_role_from(self, game: GameLite, user_id: hikari.Snowflake):
        if game.role_id is None:
            return

        await self.client.remove_role_from_member(
            game.guild_id,
            user_id,
            game.role_id,
        )

    async def remove_role(self, game: Game):
        if game.role_id is None:
            return

        await asyncio.gather(
            *[
                self.remove_role_from(game, user_id)
                for user_id in [game.author_id, *[player.user_id for player in game.players]]
            ]
        )

    async def apply_role(self, game: Game):
        if game.role_id is None:
            return

        await asyncio.gather(
            *[
                self.apply_role_to(game, user_id)
                for user_id in [game.author_id, *[player.user_id for player in game.players]]
            ]
        )

    async def apply_role_to(self, game: GameLite, user_id: hikari.Snowflake):
        if game.role_id is None:
            return

        await self.client.add_role_to_member(
            game.guild_id,
            user_id,
            game.role_id,
        )

    async def create_role(self, game: GameLite) -> hikari.Role:
        return await self.client.create_role(
            game.guild_id,
            name=game.abbreviation,
            mentionable=True,
        )

    async def create_channel_category(self, game: GameLite) -> hikari.GuildCategory:
        return await self.client.create_guild_category(
            game.guild_id,
            game.abbreviation,
            permission_overwrites=self.category_overwrites(game),
        )

    async def create_channel(
        self, game: GameLite, name: str, category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> hikari.GuildTextChannel:
        return await self.client.create_guild_text_channel(
            game.guild_id,
            name=name,
            category=category_id,
        )

    async def create_read_only_channel(
        self, game: GameLite, name: str, category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED
    ) -> hikari.GuildTextChannel:
        return await self.client.create_guild_text_channel(
            game.guild_id, name=name, category=category_id, permission_overwrites=self.read_only_overwrites(game)
        )

    async def create_voice_channel(
        self,
        game: GameLite,
        name: str,
        role_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
        category_id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
    ) -> hikari.GuildVoiceChannel:
        return await self.client.create_guild_voice_channel(
            game.guild_id,
            name=name,
            category=category_id,
            permission_overwrites=self.voice_overwrites(game, role_id),
        )

    async def full_setup(self, game: GameLite) -> None:
        category, role = await asyncio.gather(
            self.create_channel_category(game),
            self.create_role(game),
        )

        main, info, synopsis, voice = await asyncio.gather(
            self.create_read_only_channel(game, "info", category.id),
            self.create_read_only_channel(game, "synopsis", category.id),
            self.create_channel(game, "main", category.id),
            self.create_voice_channel(game, "Voice", role.id, category.id),
        )

        await self.games.update(
            game_id=game.game_id,
            guild_id=game.guild_id,
            author_id=game.author_id,
            role_id=role.id,
            category_channel_id=category.id,
            main_channel_id=main.id,
            info_channel_id=info.id,
            synopsis_channel_id=synopsis.id,
            voice_channel_id=voice.id,
        )

        game = await self.games.get(game_id=game.game_id, guild_id=game.guild_id)
        await self.apply_role(game)
