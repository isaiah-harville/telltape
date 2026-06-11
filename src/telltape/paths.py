"""Filesystem locations used by the application.

All of telltape's files live in a single directory under the user's home,
``~/.telltape``: the settings file, the editable feeds file, and cached data.
"""

from __future__ import annotations

from pathlib import Path

APP_NAME = "telltape"


def base_dir() -> Path:
    """Return the application's base directory (``~/.telltape``)."""
    return Path.home() / f".{APP_NAME}"


def config_file() -> Path:
    """Return the path to the settings file."""
    return base_dir() / "config.toml"


def feeds_file() -> Path:
    """Return the path to the feeds configuration file."""
    return base_dir() / "feeds.toml"


def cache_file(name: str) -> Path:
    """Return the path to a named cache file in the base directory.

    Args:
        name: File name to place in the base directory.
    """
    return base_dir() / name
