import os
import sys
from typing import ClassVar

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .utils import merge_dicts


class Config:
    default_config_file = os.path.join(
        os.path.expanduser("~"), ".home-media-organizer", "config.toml"
    )
    local_config_file = os.path.join(os.getcwd(), ".home-media-organizer.toml")

    allowed_commands: ClassVar = [
        "list",
        "show-exif",
        "set-exif",
        "shift-exif",
        "dedup",
        "validate",
        "rename",
        "organize",
        "cleanup",
    ]

    def __init__(self, config_file: str) -> None:
        configs = []
        for cfg in [self.default_config_file, self.local_config_file, config_file]:
            if not cfg or not os.path.isfile(cfg):
                continue
            try:
                with open(cfg, "rb") as f:
                    configs.append(tomllib.load(f))
            except tomllib.TOMLDecodeError as e:
                raise ValueError(f"Error parsing config file {cfg}: {e}") from e
        #
        # merge the list of configs into a single dictionary, including dictionaries in the values
        self.config = merge_dicts(configs)
        self.validate()

    def validate(self) -> None:
        for k in self.config:
            if k not in self.allowed_commands:
                raise ValueError(f"Unknown command {k}")
