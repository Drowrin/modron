from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    discord_token: str

    db_url: str

    @classmethod
    def load(cls, path: Path) -> Config:
        with path.open("r") as f:
            # this has to be type ignored for now, as there is an issue with types-pyyaml
            config = yaml.load(f.read(), yaml.Loader)  # type: ignore

        return cls(**config)
