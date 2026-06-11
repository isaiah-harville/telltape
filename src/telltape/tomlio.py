"""Small helpers for writing TOML.

The standard library can read TOML (``tomllib``) but not write it. Only simple,
flat documents are produced here, so a minimal quoting helper is sufficient.
"""

from __future__ import annotations


def quote(value: str) -> str:
    """Return a TOML basic string literal for a value.

    Args:
        value: Value to quote.

    Returns:
        The value wrapped in double quotes with backslashes and quotes escaped.
    """
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
