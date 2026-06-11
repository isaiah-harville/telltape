"""Feed sources and their on-disk TOML configuration.

``DEFAULT_FEEDS`` is the built-in starter set: free financial wires, general
world news that moves markets, and SEC EDGAR real-time filings. On first run it
is written to a TOML file in the application directory, which users can then edit
to add, remove, or reorder sources. ``load_feeds`` reads that file, falling back
to the defaults if it is missing or invalid.

``default_on=False`` marks high-volume feeds that start disabled so the tape is
not flooded out of the box.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .models import FILING, NEWS, WORLD, FeedSource
from .paths import feeds_file
from .tomlio import quote

# SEC fair-access policy requires a contact in the User-Agent, which the user
# supplies as their contact email in Settings. Filing feeds use a slower,
# politer interval.
_EDGAR_BASE = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&owner=include&count=40&output=atom"

DEFAULT_FEEDS: list[FeedSource] = [
    # ---- Financial wires (fast, structured) -----------------------------
    FeedSource("CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    FeedSource("CNBC Markets", "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    FeedSource("MarketWatch Top", "http://feeds.marketwatch.com/marketwatch/topstories/"),
    FeedSource("MarketWatch RealTime", "http://feeds.marketwatch.com/marketwatch/realtimeheadlines/", interval=10.0),
    FeedSource("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    FeedSource("Investing.com", "https://www.investing.com/rss/news.rss"),
    FeedSource("Seeking Alpha", "https://seekingalpha.com/feed.xml"),
    # Press-release wires — companies breaking their own news (high volume).
    FeedSource("PR Newswire", "https://www.prnewswire.com/rss/news-releases-list.rss", default_on=False),
    FeedSource(
        "GlobeNewswire",
        "https://www.globenewswire.com/RssFeed/orgclass/1/feedTitle/GlobeNewswire%20-%20News%20Room",
        default_on=False,
    ),

    # ---- World / general news that moves markets ------------------------
    FeedSource("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", category=WORLD),
    FeedSource("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", category=WORLD),
    FeedSource("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", category=WORLD),
    FeedSource("Guardian World", "https://www.theguardian.com/world/rss", category=WORLD),
    FeedSource("NYT World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", category=WORLD),
    FeedSource("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", category=WORLD),
    FeedSource("NPR News", "https://feeds.npr.org/1001/rss.xml", category=WORLD),

    # ---- SEC EDGAR real-time filings ------------------------------------
    FeedSource("EDGAR 8-K", f"{_EDGAR_BASE}&type=8-K", category=FILING, interval=20.0),
    FeedSource("EDGAR All", f"{_EDGAR_BASE}&type=", category=FILING, interval=30.0, default_on=False),
]

# Recognized categories, used to validate values read from the config file.
_CATEGORIES = {NEWS, WORLD, FILING}


def load_feeds(path: Path | None = None) -> tuple[list[FeedSource], str | None]:
    """Load feed sources from the TOML config, seeding it on first use.

    If the file does not exist, it is created from ``DEFAULT_FEEDS`` and the
    defaults are returned. If it exists but cannot be parsed, the defaults are
    returned together with a message the caller can surface, and the file is
    left untouched.

    Args:
        path: Override for the config path.

    Returns:
        A tuple of the feed sources and an optional error message.
    """
    target = path or feeds_file()
    if not target.exists():
        try:
            write_default_feeds(target)
        except OSError:
            pass
        return list(DEFAULT_FEEDS), None
    try:
        data = tomllib.loads(target.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return list(DEFAULT_FEEDS), f"Could not load feeds from {target}; using defaults."
    feeds = _parse(data)
    return (feeds or list(DEFAULT_FEEDS)), None


def write_default_feeds(path: Path) -> None:
    """Write the default feeds to a TOML file, creating parent directories.

    Args:
        path: Destination path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_toml(DEFAULT_FEEDS))


def _parse(data: dict) -> list[FeedSource]:
    """Convert parsed TOML into feed sources, skipping invalid entries."""
    feeds = []
    for row in data.get("feed", []):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        url = str(row.get("url", "")).strip()
        if not name or not url:
            continue
        category = str(row.get("category", NEWS))
        if category not in _CATEGORIES:
            category = NEWS
        try:
            interval = float(row.get("interval", 15.0))
        except (TypeError, ValueError):
            interval = 15.0
        headers = {str(k): str(v) for k, v in dict(row.get("headers", {})).items()}
        feeds.append(
            FeedSource(
                name=name,
                url=url,
                category=category,
                interval=interval,
                default_on=bool(row.get("default_on", True)),
                headers=headers,
            )
        )
    return feeds


def _render_toml(feeds: list[FeedSource]) -> str:
    """Render feed sources as a TOML document."""
    lines = [
        "# telltape feeds configuration",
        "# Edit this file to add, remove, or reorder sources, then restart.",
        "# category must be one of: news | world | filing",
        "",
    ]
    for feed in feeds:
        lines.append("[[feed]]")
        lines.append(f"name = {quote(feed.name)}")
        lines.append(f"url = {quote(feed.url)}")
        lines.append(f"category = {quote(feed.category)}")
        lines.append(f"interval = {feed.interval}")
        lines.append(f"default_on = {'true' if feed.default_on else 'false'}")
        if feed.headers:
            inner = ", ".join(f"{quote(k)} = {quote(v)}" for k, v in feed.headers.items())
            lines.append(f"headers = {{ {inner} }}")
        lines.append("")
    return "\n".join(lines)
