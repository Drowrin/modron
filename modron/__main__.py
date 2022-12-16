import argparse
import os
import sys
from pathlib import Path

import flare

from modron.app import ModronApp
from modron.config import Config

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

# load config and initialize bot
config = Config.load(args.config)
bot = ModronApp(config)
flare.install(bot)
bot.plugins.load_folder("modron.plugins")

# run forever
bot.run()
