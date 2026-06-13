"""Asynchronous feed polling.

One task is run per source, each looping on its own interval. Requests use
conditional GET (``ETag`` and ``Last-Modified``) so that an unchanged feed costs
a single ``304`` response and is only parsed when it has changed. Parsed entries
are normalized to ``Headline`` objects and placed on a shared queue. Sources can
be started and stopped at runtime, which lets the UI toggle feeds without
restarting the application.
"""

from __future__ import annotations

import asyncio
import calendar
import logging
import random
import time

import feedparser
import httpx

from .models import FILING, FeedSource, Headline
from .tickers import extract_tickers

log = logging.getLogger("telltape.poller")

# Fallback User-Agent used when no contact has been configured. Endpoints that
# require a contact (such as the SEC) will reject this; a real contact is
# supplied at runtime from user configuration.
DEFAULT_USER_AGENT = "telltape/0.1"

# Lower bound on any polling interval, so a small scale cannot hammer a feed.
_MIN_INTERVAL = 3.0


class FeedPoller:
    """Polls a set of feeds and pushes normalized headlines onto a queue."""

    def __init__(
        self,
        queue: asyncio.Queue[Headline],
        *,
        client: httpx.AsyncClient | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        interval_scale: float = 1.0,
    ) -> None:
        """Initialize the poller.

        Args:
            queue: Queue that received headlines are placed on.
            client: HTTP client to use. If omitted, one is created and owned by
                the poller and closed on ``aclose``.
            user_agent: User-Agent sent with every request.
            interval_scale: Multiplier applied to non-filing intervals; below 1
                polls faster. SEC filing feeds ignore it for fair-access safety.
        """
        self.queue = queue
        self.user_agent = user_agent
        self.interval_scale = interval_scale
        self._client = client
        self._owns_client = client is None
        self._tasks: dict[str, asyncio.Task[None]] = {}
        # Conditional-GET validators keyed by URL, retained across restarts of a
        # source so a re-enabled feed does not re-deliver everything.
        self._etag: dict[str, str] = {}
        self._modified: dict[str, str] = {}

    @property
    def active(self) -> set[str]:
        """Return the names of currently running sources."""
        return set(self._tasks)

    def set_user_agent(self, user_agent: str) -> None:
        """Update the User-Agent for subsequent requests.

        Args:
            user_agent: New User-Agent string. Applied immediately to the active
                client, if any, without dropping connections.
        """
        self.user_agent = user_agent
        if self._client is not None:
            self._client.headers["User-Agent"] = user_agent

    def start(self, src: FeedSource) -> None:
        """Begin polling a source.

        Args:
            src: Source to poll. Has no effect if it is already running.
        """
        if src.name in self._tasks:
            return
        self._ensure_client()
        self._tasks[src.name] = asyncio.create_task(
            self._poll_loop(src), name=f"poll:{src.name}"
        )

    def stop(self, name: str) -> None:
        """Stop polling a source.

        Args:
            name: Name of the source. Has no effect if it is not running.
        """
        task = self._tasks.pop(name, None)
        if task is not None:
            task.cancel()

    async def aclose(self) -> None:
        """Cancel all poll tasks and close the client if owned."""
        for task in list(self._tasks.values()):
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> None:
        """Create the HTTP client on first use."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
            )

    def _interval(self, src: FeedSource) -> float:
        """Return the effective poll interval for a source.

        The configured ``interval_scale`` speeds up or slows down ordinary
        feeds, clamped to a floor. SEC filing feeds are left at their configured
        interval regardless, to respect the SEC's fair-access policy.
        """
        if src.category == FILING:
            return src.interval
        return max(_MIN_INTERVAL, src.interval * self.interval_scale)

    async def _poll_loop(self, src: FeedSource) -> None:
        """Poll a single source forever at its effective interval."""
        # Stagger startup so that not every feed is requested at once.
        await asyncio.sleep(random.uniform(0, min(self._interval(src), 3.0)))
        while True:
            started = time.monotonic()
            try:
                await self._poll_once(src)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # A single failing feed must not affect the others.
                log.warning("poll failed for %s: %s", src.name, exc)
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.0, self._interval(src) - elapsed))

    async def _poll_once(self, src: FeedSource) -> None:
        """Fetch a source once and enqueue any new entries."""
        assert self._client is not None
        headers = dict(src.headers)
        if etag := self._etag.get(src.url):
            headers["If-None-Match"] = etag
        if modified := self._modified.get(src.url):
            headers["If-Modified-Since"] = modified

        resp = await self._client.get(src.url, headers=headers)
        if resp.status_code == 304:
            return
        resp.raise_for_status()

        if etag := resp.headers.get("ETag"):
            self._etag[src.url] = etag
        if modified := resp.headers.get("Last-Modified"):
            self._modified[src.url] = modified

        parsed = feedparser.parse(resp.content)
        fetched = time.time()
        headlines = [
            headline
            for entry in parsed.entries
            if (headline := self._to_headline(src, entry, fetched)) is not None
        ]
        # Feeds list entries newest-first (and the order is not guaranteed), but
        # the tape is a chronological stream. Emit oldest-first so the newest of
        # a batch lands at the bottom. Entries without a timestamp are treated as
        # current and placed last.
        headlines.sort(key=lambda h: (h.ts_published is None, h.ts_published or 0.0))
        for headline in headlines:
            await self.queue.put(headline)

    @staticmethod
    def _to_headline(src: FeedSource, entry, fetched: float) -> Headline | None:
        """Convert a feedparser entry into a ``Headline``.

        Args:
            src: Source the entry came from.
            entry: A feedparser entry.
            fetched: Fetch time in epoch seconds.

        Returns:
            A normalized headline, or ``None`` if the entry has no title.
        """
        title = (entry.get("title") or "").strip()
        if not title:
            return None
        summary = (entry.get("summary") or "").strip()

        ts_published: float | None = None
        for key in ("published_parsed", "updated_parsed"):
            # Read raw keys via ``dict.get`` rather than ``entry.get``: feedparser
            # otherwise applies a deprecated alias mapping ``updated_parsed`` to
            # ``published_parsed``, which warns whenever a feed carries a blank or
            # unparseable date.
            parsed_time = dict.get(entry, key)
            if parsed_time:
                # feedparser normalizes parsed times to a UTC struct_time.
                ts_published = float(calendar.timegm(parsed_time))
                break

        return Headline(
            source=src.name,
            title=title,
            url=entry.get("link") or "",
            summary=summary,
            category=src.category,
            ts_published=ts_published,
            ts_fetched=fetched,
            tickers=extract_tickers(title, summary),
        )
