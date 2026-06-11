"""The headline pipeline: poll, deduplicate, and dispatch.

``NewsEngine`` ties the poller, the deduper, and a caller-supplied callback
together. It is independent of any user interface: the callback decides what to
do with each new headline. Sources can be enabled and disabled while running.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Iterable
from typing import Callable

from .dedup import Deduper
from .models import FeedSource, Headline
from .poller import DEFAULT_USER_AGENT, FeedPoller

log = logging.getLogger("telltape.engine")

# A handler may be synchronous or asynchronous; an awaitable result is awaited.
HeadlineHandler = Callable[[Headline], "None | Awaitable[None]"]


class NewsEngine:
    """Coordinates polling, deduplication, and headline dispatch."""

    def __init__(
        self,
        *,
        on_headline: HeadlineHandler,
        user_agent: str = DEFAULT_USER_AGENT,
        dedup_capacity: int = 5000,
        dedup_threshold: float = 88.0,
        max_age: float | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            on_headline: Callback invoked once per new headline.
            user_agent: User-Agent passed to the poller.
            dedup_capacity: Maximum number of exact titles remembered.
            dedup_threshold: Fuzzy-match similarity threshold (0-100).
            max_age: If set, headlines already older than this many seconds when
                received are dropped. Useful for suppressing the backlog a feed
                returns on its first poll.
        """
        self.on_headline = on_headline
        self.max_age = max_age
        self.queue: asyncio.Queue[Headline] = asyncio.Queue()
        self.deduper = Deduper(capacity=dedup_capacity, threshold=dedup_threshold)
        self.poller = FeedPoller(self.queue, user_agent=user_agent)
        self._sources: dict[str, FeedSource] = {}
        self._consumer: asyncio.Task[None] | None = None

    @property
    def active_names(self) -> set[str]:
        """Return the names of currently enabled sources."""
        return set(self._sources)

    def set_user_agent(self, user_agent: str) -> None:
        """Update the User-Agent used for requests."""
        self.poller.set_user_agent(user_agent)

    def enable(self, src: FeedSource) -> None:
        """Enable a source and begin polling it."""
        if src.name not in self._sources:
            self._sources[src.name] = src
            self.poller.start(src)

    def disable(self, name: str) -> None:
        """Disable a source and stop polling it."""
        if self._sources.pop(name, None) is not None:
            self.poller.stop(name)

    async def run(self, initial: Iterable[FeedSource] = ()) -> None:
        """Run until cancelled, then release resources.

        Args:
            initial: Sources to enable on startup.
        """
        self._consumer = asyncio.create_task(self._consume())
        for src in initial:
            self.enable(src)
        try:
            await asyncio.Event().wait()
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """Stop polling and cancel the consumer task."""
        await self.poller.aclose()
        if self._consumer is not None:
            self._consumer.cancel()
            await asyncio.gather(self._consumer, return_exceptions=True)
            self._consumer = None

    async def _consume(self) -> None:
        """Drain the queue, dropping duplicates and stale items."""
        while True:
            headline = await self.queue.get()
            if not self.deduper.is_new(headline.normalized_title):
                continue
            if self.max_age is not None:
                age = headline.age
                if age is not None and age > self.max_age:
                    continue
            try:
                result = self.on_headline(headline)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                # A failing handler must not stop the pipeline.
                log.exception("on_headline callback failed")
