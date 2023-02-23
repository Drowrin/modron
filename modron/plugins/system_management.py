from __future__ import annotations

import typing

import crescent
import flare
import hikari

from modron.db import System, SystemLite
from modron.model import ModronPlugin

plugin = ModronPlugin()
system = crescent.Group(
    "system",
    "system management",
    dm_enabled=False,
    default_member_permissions=(hikari.Permissions.ADMINISTRATOR),
)


class SystemConverter(flare.Converter[System]):
    async def to_str(self, obj: System) -> str:
        return f"{obj.guild_id}:{obj.system_id}"

    async def from_str(self, obj: str) -> System:
        guild_id, system_id = obj.split(":")
        return await plugin.model.systems.get(int(system_id), int(guild_id))


class SystemLiteConverter(flare.Converter[SystemLite]):
    async def to_str(self, obj: SystemLite) -> str:
        return f"{obj.guild_id}:{obj.system_id}"

    async def from_str(self, obj: str) -> SystemLite:
        guild_id, system_id = obj.split(":")
        return await plugin.model.systems.get_lite(int(system_id), int(guild_id))


flare.add_converter(System, SystemConverter)
flare.add_converter(SystemLite, SystemLiteConverter)


async def system_display(system: System) -> typing.Sequence[hikari.Embed]:
    pass


async def system_main_menu(system: System) -> typing.Sequence[hikari.api.ComponentBuilder]:
    pass


# @plugin.include
# @system.child
# @crescent.command(name="")
# class
