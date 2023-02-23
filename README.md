<div align="center">

# Modron

[![ci](https://github.com/drowrin/modron/actions/workflows/ci.yml/badge.svg)](https://github.com/drowrin/modron/actions/workflows/ci.yml)
![code-style-black](https://badgen.net/badge/code-style/black/black)
![python-version-3.11](https://badgen.net/badge/python/3%2E11/blue)

A Discord bot providing organization tools for TTRPG groups.

</div>

## Features and Roadmap

This project is currently very early in development.

- [x] Suggestion and feedback channels
  - Allow users to create tickets for feedback, suggestions, concerns, or ideas
  - Anonymous posting and messaging options
  - Unlimited feedback channels per guild, allowing you to organize by whatever categories you need
  - Completely stateless--nothing from this feature is cached or stored by the bot
- [ ] Game management
  - Display information on each game in a server
  - Provide an interface to edit game details and settings
  - Creation and management of categories, channels, and roles
  - Provide an interface for players to join games
  - Provide an interface for GMs to manually add players
- [ ] Character database
  - Display name, brief and long descriptions, optionally an image, optionally pronouns
  - Decoupled character and player lists
  - Keep track of original character author, even if transferred to another player
- [ ] Safety tool management
  - Keep track of safety tool information per-game
  - Easy, anonymous additions
- [ ] Session management
  - Keep track of sessions and display using discord events
  - Allow for postponement or rescheduling
  - Set nicknames of players to character names during a session
  - Tools for organizing session recap/synopses
  - Automatic links to livestreams
  - Ready Check
    - Ping participants of a game ahead of time
    - Gather responses from participants
      - Yes
      - Yes, but `<user input>`
      - No, because `<user input>`
    - Show results at a glance

## Development

To install all dependencies, simply run

```sh
pip install -r requirements/all.txt
```

You'll also need to create a copy of `example.config.yml` and fill in all missing values.

To run the project locally:

```
python -m modron -c path/to/your/config.yml
```

This project also uses [Nox](https://nox.thea.codes/en/stable/) to automate some development tools. To run these tools:

```sh
# run code style, spell check, and lint
nox -s lint
# run type checking
nox -s typecheck
# run tools to automatically/interactively fix some style, spelling, and lint issues
nox -s fixes
```

## Thanks

This project is powered by the *awesome projects* [Hikari](https://github.com/hikari-py/hikari), [Crescent](https://github.com/magpie-dev/hikari-crescent), and [Flare](https://github.com/brazier-dev/hikari-flare).
