"""Persistent user settings stored as JSON in the platform config directory."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "mov-compress"
DEFAULT_TARGET_MB = 30.0


def config_file() -> Path:
    """Return the path of the settings file for the current platform."""
    return Path(user_config_dir(APP_NAME)) / "config.json"


@dataclass
class Settings:
    """User preferences that survive between runs."""

    target_mb: float = DEFAULT_TARGET_MB
    output_dir: str = ""
    browse_dir: str = ""

    @classmethod
    def load(cls) -> Settings:
        """Load settings from disk, falling back to defaults on any problem."""
        try:
            raw = json.loads(config_file().read_text())
        except (OSError, ValueError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        try:
            return cls(**{k: v for k, v in raw.items() if k in known})
        except TypeError:
            return cls()

    def save(self) -> None:
        """Write settings to disk, ignoring an unwritable config directory."""
        path = config_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(asdict(self), indent=2))
        except OSError:
            pass
