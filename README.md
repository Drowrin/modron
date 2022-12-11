<div align="center">

# Modron

[![ci](https://github.com/drowrin/modron/actions/workflows/ci.yml/badge.svg)](https://github.com/drowrin/modron/actions/workflows/ci.yml)
![mypy](https://badgen.net/badge/mypy/checked/)
![code-style-black](https://badgen.net/badge/code-style/black/black)
![python-version-3.11](https://badgen.net/badge/python/3%2E11/blue)

A Discord bot providing organization tools for TTRPG groups.

</div>

## Features and Roadmap

This project is currently very early in development.

- [x] Suggestion and feedback channels
  - [x] Allow users to create tickets for feedback, suggestions, concerns, or ideas
  - [x] Anonymous posting and messaging options
  - [x] Unlimited feedback channels per guild, allowing you to organize by whatever categories you need
  - [x] Completely stateless--nothing from this feature is cached or stored by the bot
- [ ] Game management
  - [ ] Creation and management of categories, channels, and roles for game groups
  - [ ] Provide an interface for players to join games
  - [ ] Character database
  - [ ] Decoupled character and player lists
- [ ] Safety tool management
  - [ ] Keep track of safety tool information per-game
  - [ ] Easy, anonymous additions
- [ ] Session management
  - [ ] Keep track of sessions and display using discord events
  - [ ] Allow for postponement or rescheduling
  - [ ] Set nicknames of players to character names during a session
  - [ ] Tools for organizing session recap/synopses
  - [ ] Automatic links to livestreams
  - [ ] Ready Check
    - [ ] Ping participants of a game ahead of time
    - [ ] Gather responses from participants
      - [ ] Yes
      - [ ] Yes, but `<user input>`
      - [ ] No, because `<user input>`
    - [ ] Show results at a glance

## Development

This project uses [Poetry](https://python-poetry.org/) for dependency management. To install all dependencies, simply run

```sh
poetry install
```

You'll also need to create a copy of `example.config.yml` and fill in all missing values.

To run the project locally:

```
poetry run python -m modron -c path/to/your/config.yml
```

This project also uses [Nox](https://nox.thea.codes/en/stable/) to automate some development tools. To run these tools:

```sh
# run code style, spellikng, and typing checks
poetry run nox -s lint
# run tools to automatically/interactively fix some style and spelling issues
poetry run nox -s fixes
```

## Thanks

This project is powered by the *awesome projects* [Hikari](https://github.com/hikari-py/hikari), [Crescent](https://github.com/magpie-dev/hikari-crescent), and [Flare](https://github.com/brazier-dev/hikari-flare).
