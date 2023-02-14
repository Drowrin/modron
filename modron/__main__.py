import argparse
import os
import sys
from pathlib import Path

import crescent
import flare
import hikari

from modron.config import Config
from modron.exceptions import ModronError
from modron.model import Model

# CLI args
parser = argparse.ArgumentParser(prog="Modron", description="CLI for running the Modron discord bot")
parser.add_argument(
    "-c", "--config", type=Path, help="path to the config file", default=Path("config.yml"), dest="config"
)
args = parser.parse_args()

# install uvloop if available
if os.name != "nt":
    import uvloop

    uvloop.install()

# check if config file exists
if not args.config.exists() or not args.config.is_file():
    sys.exit(f"config path {str(args.config)} does not point to a file")

# load config
config = Config.load(args.config)

# create global model
model = Model(config)

# initialize bot, plugins, and hikari extension libraries
bot = hikari.GatewayBot(
    token=config.discord_token,
)
flare.install(bot)
client = crescent.Client(bot, model=model)
client.plugins.load_folder("modron.plugins")


@bot.listen()
async def on_start(_: hikari.StartingEvent) -> None:
    """
    While the bot is starting, initialize async resources such as database connections.
    """
    await model.start()


@bot.listen(hikari.ExceptionEvent)
async def on_modron_error(event: hikari.ExceptionEvent[hikari.Event]):
    """
    If an error is raised that the bot can report to the user, report it to the user.
    Otherwise, rereaise the exception.
    """
    if not isinstance(event.exception, ModronError) or not isinstance(event.failed_event, hikari.InteractionCreateEvent):
        raise event.exception

    interaction = event.failed_event.interaction
    await event.app.rest.create_interaction_response(
        interaction, interaction.token, hikari.ResponseType.MESSAGE_CREATE, **event.exception.to_response_args()
    )


# run forever
bot.run()
