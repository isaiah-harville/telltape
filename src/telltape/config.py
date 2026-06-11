"""Persistent user settings, stored as TOML in the application directory.

The most important setting is the contact email used in the outgoing
User-Agent: data providers such as the SEC require a contact and may throttle or
block a contact shared across too many clients, so each user supplies their own.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields

from .paths import config_file
from .tomlio import quote

DEFAULT_THEME = "nord"
_UA_VERSION = "0.1"


@dataclass
class Config:
    """User-configurable settings.

    Attributes:
        contact_email: Email included in the User-Agent so data providers can
            identify the client. Required for SEC endpoints.
        theme: Name of the Textual theme to use for the interface.
        alerts_sound: Whether to ring the terminal bell on an alert match.
        fuzzy_threshold: Similarity score (0-100) at or above which two
            headlines are treated as duplicates.
    """

    contact_email: str = ""
    theme: str = DEFAULT_THEME
    alerts_sound: bool = True
    fuzzy_threshold: float = 88.0

    @property
    def user_agent(self) -> str:
        """Return the User-Agent string to send with requests.

        Includes the contact email when one is configured, which is what data
        providers expect for attribution and rate-limit accounting.
        """
        contact = self.contact_email.strip()
        base = f"telltape/{_UA_VERSION}"
        return f"{base} {contact}" if contact else base


def load_config() -> tuple[Config, str | None]:
    """Load settings from disk.

    A missing file is not an error and yields defaults silently. A file that
    exists but cannot be parsed yields defaults together with a message the
    caller can surface to the user.

    Returns:
        A tuple of the settings and an optional error message.
    """
    path = config_file()
    if not path.exists():
        return Config(), None
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return Config(), f"Could not load settings from {path}; using defaults."
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known}), None


def save_config(config: Config) -> None:
    """Write settings to disk, creating the directory if needed.

    Args:
        config: Settings to persist.
    """
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_toml(config))


def _render_toml(config: Config) -> str:
    """Render settings as a flat TOML document."""
    lines = [
        "# telltape settings",
        f"contact_email = {quote(config.contact_email)}",
        f"theme = {quote(config.theme)}",
        f"alerts_sound = {'true' if config.alerts_sound else 'false'}",
        f"fuzzy_threshold = {config.fuzzy_threshold}",
    ]
    return "\n".join(lines) + "\n"
