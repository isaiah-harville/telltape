"""Core data types shared across the application.

This module defines the two structures the rest of the pipeline operates on: a
``FeedSource`` describing where to poll, and a ``Headline`` describing a single
normalized news item.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

# Headline categories. These are plain strings rather than an enum so that
# configuration files and new sources can introduce categories without code
# changes.
NEWS = "news"
"""Market, company, and business wire coverage."""

WORLD = "world"
"""General world news that can move markets, such as war or policy changes."""

FILING = "filing"
"""SEC EDGAR regulatory filings."""


@dataclass(frozen=True, slots=True)
class FeedSource:
    """A single RSS or Atom endpoint to poll.

    Attributes:
        name: Human-readable label shown in the UI and used as a key.
        url: Feed URL to fetch.
        category: One of ``NEWS``, ``WORLD``, or ``FILING``.
        group: Free-form label used to organize sources in the catalog screen,
            such as "Wires" or "Crypto". Purely cosmetic; the engine ignores it.
        interval: Minimum seconds between polls for this source.
        default_on: Whether the source starts enabled in the UI. High-volume
            feeds default to ``False`` so they do not flood the tape.
        headers: Per-source HTTP header overrides.
    """

    name: str
    url: str
    category: str = NEWS
    group: str = ""
    interval: float = 15.0
    default_on: bool = True
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Headline:
    """A normalized news item produced from one feed entry.

    Two timestamps are tracked so the UI can report freshness: ``ts_published``
    is when the source says the item was published, and ``ts_fetched`` is when
    this application first retrieved it. The difference is the end-to-end
    latency surfaced as the item's age.

    Attributes:
        source: Name of the originating feed.
        title: Headline text.
        url: Link to the full item.
        summary: Optional short description from the feed.
        category: Category inherited from the source.
        ts_published: Publication time in epoch seconds (UTC), or ``None`` if
            the feed did not provide one.
        ts_fetched: Time this item was fetched, in epoch seconds.
        tickers: Stock symbols detected in the item.
    """

    source: str
    title: str
    url: str
    summary: str = ""
    category: str = NEWS
    ts_published: float | None = None
    ts_fetched: float = field(default_factory=time.time)
    tickers: tuple[str, ...] = ()

    @property
    def normalized_title(self) -> str:
        """Return the title lowercased with collapsed whitespace.

        Used for both exact and fuzzy deduplication so that trivial formatting
        differences do not defeat duplicate detection.
        """
        return " ".join(self.title.lower().split())

    @property
    def id(self) -> str:
        """Return a stable hash of the normalized title.

        The hash intentionally ignores the URL so that the same story published
        across multiple wires collapses to a single identifier.
        """
        return hashlib.sha1(self.normalized_title.encode("utf-8")).hexdigest()

    @property
    def age(self) -> float | None:
        """Return seconds since publication, or ``None`` if unknown."""
        if self.ts_published is None:
            return None
        return max(0.0, time.time() - self.ts_published)
