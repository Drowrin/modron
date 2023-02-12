import crescent
import hikari

from modron.menus.feedback import delete_feedback_menu, send_feedback_menu
from modron.utils import get_me

plugin = crescent.Plugin[hikari.GatewayBot, None]()
feedback = crescent.Group(
    "feedback",
    "feedback channel management",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.MANAGE_MESSAGES,
)


@plugin.include
@feedback.child
@crescent.command(name="start", description="convert this channel into a feedback channel")
class FeedbackStart:
    set_permissions = crescent.option(
        bool,
        "if True, permissions for this channel will be altered",
        default=True,
    )

    async def callback(self, ctx: crescent.Context) -> None:
        # immediately defer with an ephemeral message so that the response is above the menu
        await ctx.defer(ephemeral=True)

        if self.set_permissions:
            # this command can only be used in guilds, as set in the `feedback` crescent.Group above
            assert ctx.guild_id is not None

            # get the bot user
            me = await get_me(ctx.app)

            # set the channel permissions to disallow normal conversation from users
            # but allow the bot to create threads for discussion to happen in
            await ctx.app.rest.edit_channel(
                ctx.channel_id,
                permission_overwrites=[
                    hikari.PermissionOverwrite(
                        id=ctx.guild_id,
                        type=hikari.PermissionOverwriteType.ROLE,
                        deny=(
                            hikari.Permissions.CREATE_PUBLIC_THREADS
                            | hikari.Permissions.CREATE_PRIVATE_THREADS
                            | hikari.Permissions.SEND_MESSAGES
                        ),
                        allow=hikari.Permissions.SEND_MESSAGES_IN_THREADS,
                    ),
                    hikari.PermissionOverwrite(
                        id=me.id,
                        type=hikari.PermissionOverwriteType.MEMBER,
                        allow=(
                            hikari.Permissions.CREATE_PUBLIC_THREADS
                            | hikari.Permissions.CREATE_PRIVATE_THREADS
                            | hikari.Permissions.SEND_MESSAGES
                        ),
                    ),
                ],
            )

        # send the feedback menu to the current channel
        await send_feedback_menu(ctx.app, ctx.channel_id)

        # let the user know how they can easily undo the changes done by this command
        await ctx.respond("Success! You can turn this back into a normal channel with `/feedback stop`", ephemeral=True)


@plugin.include
@feedback.child
@crescent.command(name="stop", description="convert this channel back into a regular channel")
class FeedbackStop:
    async def callback(self, ctx: crescent.Context) -> None:
        # this command can only be used in guilds, as set in the `feedback` crescent.Group above
        assert ctx.guild_id is not None

        # reset the channel permissions to defaults
        await ctx.app.rest.edit_channel(ctx.channel_id, permission_overwrites=[])

        # delete the feedback menu
        await delete_feedback_menu(ctx.app, ctx.channel_id)

        await ctx.respond("Success! This channel has been converted to a regular channel.", ephemeral=True)
