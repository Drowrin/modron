import asyncio

import crescent
import flare
import hikari

plugin = crescent.Plugin()
feedback = crescent.Group(
    "feedback",
    "feedback channel management",
    dm_enabled=False,
    default_member_permissions=hikari.Permissions.MANAGE_CHANNELS | hikari.Permissions.MANAGE_MESSAGES,
)


async def get_me(app: hikari.RESTAware) -> hikari.OwnUser:
    """
    Get the bot user from the cache if available, otherwise fetch it.
    """
    if isinstance(app, hikari.CacheAware):
        return app.cache.get_me() or await app.rest.fetch_my_user()
    else:
        return await app.rest.fetch_my_user()


@flare.button(label="Delete Anonymous Message", style=hikari.ButtonStyle.DANGER)
async def delete_anonymous_button(ctx: flare.MessageContext, message_id: hikari.Snowflake) -> None:
    """
    This button provides a user the ability to delete a specific message.
    The message id is serialized in the button's custom_id.
    """
    try:
        await ctx.app.rest.delete_message(ctx.channel_id, message_id)
    except hikari.NotFoundError:
        response = await ctx.respond(
            "That message was already deleted!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
    else:
        response = await ctx.respond(
            "Successfully deleted the anonymous message!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )

    # This message is just a notification. We can remove it after a short delay.
    await asyncio.sleep(5)
    await response.delete()


class AnonymousMessageModal(flare.Modal, title="Send Anonymous Message"):
    """
    This modal lets the user send an anonymous message in the current channel.
    """

    content: flare.TextInput = flare.TextInput(
        label="Message Content",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=1,
        max_length=4000,
        required=True,
        placeholder="This message will be sent to the channel anonymously!",
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        # send the anonymous message
        embed = hikari.Embed(description=self.content.value).set_author(name="Anonymous Message")
        message = await ctx.app.rest.create_message(ctx.channel_id, embed=embed)

        # send the delete message menu to only the user who sent the message
        row = await flare.Row(delete_anonymous_button(message.id))
        await ctx.respond(
            flags=hikari.MessageFlag.EPHEMERAL,
            component=row,
        )

        # move the anonymous message menu to the bottom of the channel
        await delete_anon_menu(ctx.app, ctx.channel_id)
        await send_anon_menu(ctx.app, ctx.channel_id)


@flare.button(label="Send Anonymous Message", style=hikari.ButtonStyle.SECONDARY)
async def anonymous_button(ctx: flare.MessageContext) -> None:
    """
    This button sends a modal to the user that lets them send an anonymous message in the current channel.
    """
    await AnonymousMessageModal().send(ctx.interaction)


async def send_anon_menu(app: hikari.RESTAware, channel_id: hikari.Snowflake) -> hikari.Message:
    """
    Send a menu to a channel which lets users send anonymous messages in that channel.
    """
    row = await flare.Row(anonymous_button())
    return await app.rest.create_message(channel_id, component=row)


async def delete_anon_menu(app: hikari.RESTAware, channel_id: hikari.Snowflake) -> None:
    """
    Find the most recently sent anonymous message menu sent in the channel, and delete it.
    Only searches the most recent 5 messages.
    """
    # get the bot user before the loop
    me = await get_me(app)

    # iterate through the 5 most recent messages in the channel
    async for message in app.rest.fetch_messages(channel=channel_id).limit(5):
        # skip if the message is not from the bot
        if message.author.id != me.id:
            continue

        # skip if the message has the wrong number of components
        if len(message.components) != 1 or len(message.components[0].components) != 1:
            continue

        # delete the message if its component labels match expectations
        maybe_anon_button = message.components[0].components[0]
        if (
            isinstance(maybe_anon_button, hikari.ButtonComponent)
            and maybe_anon_button.label == "Send Anonymous Message"
        ):
            await message.delete()
            break


class ConfirmationModal(flare.Modal, title="Are you sure?"):
    """
    A confirmation dialog requiring the user to be very intentional when deleting a thread.
    """

    thread_id: hikari.Snowflake

    confirmation: flare.TextInput = flare.TextInput(
        label='Type "DELETE" to confirm',
        style=hikari.TextInputStyle.SHORT,
        required=True,
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        # check if user input matches DELETE
        if self.confirmation.value == "DELETE":
            # delete the thread
            await ctx.app.rest.delete_channel(self.thread_id)
            # delete the "<bot_name> started a thread: <thread_title>" message
            await ctx.app.rest.delete_message(ctx.channel_id, self.thread_id)
            response = await ctx.respond(
                "Thread deleted!",
                flags=hikari.MessageFlag.EPHEMERAL,
            )
        else:
            # Tell the user that why the thread was not deleted
            response = await ctx.respond("Confirmation did not match `DELETE`.", flags=hikari.MessageFlag.EPHEMERAL)

        # This message is just a notification. We can remove it after a short delay.
        await asyncio.sleep(5)
        await response.delete()


@flare.button(label="Delete Feedback Thread", style=hikari.ButtonStyle.DANGER)
async def delete_feedback_button(ctx: flare.MessageContext, thread_id: hikari.Snowflake) -> None:
    """
    his button provides a user the ability to delete a specific thread.
    The thread id is serialized in the button's custom_id.
    The user must complete a confirmation dialog first, in order to prevent accidental deletion.
    """
    try:
        await ctx.app.rest.fetch_channel(thread_id)
    except hikari.NotFoundError:
        response = await ctx.respond(
            "That thread was already deleted!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        await asyncio.sleep(5)
        await response.delete()
    else:
        await ConfirmationModal(thread_id=thread_id).send(ctx.interaction)


class FeedbackModal(flare.Modal, title="Send Feedback"):
    """
    This modal gives a user the ability to start a feedback thread, possibly anonymously.
    An anonymous message button menu will also be sent to the new thread.
    """

    anonymous: bool

    name: flare.TextInput = flare.TextInput(
        label="Title",
        style=hikari.TextInputStyle.SHORT,
        min_length=1,
        max_length=100,
        required=True,
        placeholder="The title of the thread.",
    )

    content: flare.TextInput = flare.TextInput(
        label="Content",
        style=hikari.TextInputStyle.PARAGRAPH,
        min_length=1,
        max_length=4000,
        required=True,
        placeholder="The content of the feedback message you want to send.",
    )

    async def callback(self, ctx: flare.ModalContext) -> None:
        # these are marked as required above, so they shouldn't be None
        assert self.name.value is not None
        assert self.content.value is not None

        # create the thread with the name the user set
        thread = await ctx.app.rest.create_thread(
            ctx.channel_id,
            hikari.ChannelType.GUILD_PUBLIC_THREAD,
            self.name.value,
        )

        # send the delete thread menu to only the user who started the thread
        manage_feedback_menu = await flare.Row(delete_feedback_button(thread_id=thread.id))
        await ctx.respond(
            flags=hikari.MessageFlag.EPHEMERAL,
            component=manage_feedback_menu,
        )

        # create an embed containing the message set by the user
        feedback_embed = hikari.Embed(
            description=self.content.value,
        )

        if self.anonymous:
            # anonymous messages all have "Anonymous Message" for an author
            feedback_embed.set_author(
                name="Anonymous Message",
            )
        else:
            # these interactions can only happen in guilds, as set in the `feedback` crescent.Group above
            assert ctx.guild_id is not None

            # attempt to get guild-specific information, with interaction-provided information as a fallback
            if (
                isinstance(ctx.app, hikari.CacheAware)
                and (member := ctx.app.cache.get_member(ctx.guild_id, ctx.author)) is not None
            ):
                feedback_embed.set_author(
                    name=member.nickname or member.username,
                    icon=member.guild_avatar_url or member.display_avatar_url,
                )
            else:
                feedback_embed.set_author(
                    name=ctx.author.username,
                    icon=ctx.author.avatar_url,
                )

        # send a message using the embed generated above
        await ctx.app.rest.create_message(
            thread.id,
            embed=feedback_embed,
        )

        # send the anonymous message menu to the thread
        await send_anon_menu(ctx.app, thread.id)

        # move the feedback menu to the bottom of the channel
        await delete_feedback_menu(ctx.app, ctx.channel_id)
        await send_feedback_menu(ctx.app, ctx.channel_id)


@flare.button()
async def feedback_button(ctx: flare.MessageContext, anonymous: bool) -> None:
    """
    This button sends the user a modal that allows them to create a (possibly anonymous) feedback thread.
    """
    modal = FeedbackModal(anonymous=anonymous)

    # Overwrite the modal title if it is anonymous
    if anonymous:
        modal.set_title("Send Anonymous Feedback")

    await modal.send(ctx.interaction)


async def send_feedback_menu(app: hikari.RESTAware, channel_id: hikari.Snowflake) -> hikari.Message:
    """
    Send a menu to a channel that lets users create (possibly anonymous) feedback threads.
    """
    embed = hikari.Embed(
        title="Feedback Menu",
        description=(
            "This channel can be used for feedback or suggestions!" "\nAnonymous messages are not tied to your account."
        ),
    ).set_footer("Click one of the buttons below to send a message!")

    row = await flare.Row(
        feedback_button(anonymous=False).set_label("Send Feedback").set_style(hikari.ButtonStyle.PRIMARY),
        feedback_button(anonymous=True).set_label("Send Anonymous Feedback").set_style(hikari.ButtonStyle.SECONDARY),
    )

    # send a message with brief instructions/information and buttons
    return await app.rest.create_message(channel_id, embed=embed, component=row)


async def delete_feedback_menu(app: hikari.RESTAware, channel_id: hikari.Snowflake) -> None:
    """
    Find the most recently sent feedback menu sent in the channel, and delete it.
    Only searches the most recent 5 messages.
    """
    # get the bot user before the loop
    me = await get_me(app)

    # iterate through the 5 most recent messages in the channel
    async for message in app.rest.fetch_messages(channel=channel_id).limit(5):
        # skip if the message is not from the bot
        if message.author.id != me.id:
            continue

        # skip if the message has the wrong number of components
        if len(message.components) != 1 or len(message.components[0].components) != 2:
            continue

        # delete the message if its component labels match expectations
        maybe_feedback_button = message.components[0].components[0]
        maybe_anon_button = message.components[0].components[1]
        if (
            isinstance(maybe_feedback_button, hikari.ButtonComponent)
            and maybe_feedback_button.label == "Send Feedback"
            and isinstance(maybe_anon_button, hikari.ButtonComponent)
            and maybe_anon_button.label == "Send Anonymous Feedback"
        ):
            await message.delete()
            break


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
