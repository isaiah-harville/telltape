"""Rendering of headlines to Rich renderables for display in the TUI."""

from __future__ import annotations

from datetime import datetime

from rich.style import Style
from rich.text import Text

from .models import FILING, WORLD, Headline

# Accent style per category, with a default for ordinary news.
_CATEGORY_STYLE = {FILING: "bold magenta", WORLD: "blue"}
_DEFAULT_STYLE = "cyan"


def _age_str(headline: Headline) -> str:
    """Return a fixed-width, human-readable age for a headline."""
    age = headline.age
    if age is None:
        return "  --  "
    if age < 60:
        return f"{age:4.0f}s "
    if age < 3600:
        return f"{age / 60:4.0f}m "
    return f"{age / 3600:4.0f}h "


def format_headline(headline: Headline, *, keyword: str = "", alert: bool = False) -> Text:
    """Render a headline as a single styled line.

    Args:
        headline: Headline to render.
        keyword: Optional term to highlight wherever it appears in the line.
        alert: Whether this headline matched an alert rule, in which case it is
            marked and emphasized.

    Returns:
        A Rich ``Text`` containing the time, age, source, title, and any
        detected cashtags.
    """
    line = Text()
    if alert:
        line.append("● ", style="bold red")
    line.append(datetime.now().strftime("%H:%M:%S "), style="dim")
    line.append(_age_str(headline), style="yellow")
    style = _CATEGORY_STYLE.get(headline.category, _DEFAULT_STYLE)
    line.append(f"{headline.source:<20.20} ", style=style)
    line.append(headline.title.strip(), style="bold" if alert else "")
    if keyword:
        line.highlight_words([keyword], "black on yellow", case_sensitive=False)
    if headline.tickers:
        line.append("  " + " ".join(f"${t}" for t in headline.tickers), style="bold green")
    # Carry the source URL on the whole line so a double-click can open it. The
    # meta merges onto the existing styles without disturbing colors.
    if headline.url:
        line.stylize(Style(meta={"url": headline.url}))
    return line
