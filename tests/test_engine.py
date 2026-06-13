"""Tests for the headline pipeline (dedup + dispatch)."""

from __future__ import annotations

import asyncio
import time

from telltape.engine import NewsEngine

from .conftest import make_headline


async def _run_consumer(engine: NewsEngine, until_count, received, timeout=1.0):
    """Run the engine's consumer until ``received`` reaches a length or timeout."""
    task = asyncio.create_task(engine._consume())
    try:
        deadline = asyncio.get_event_loop().time() + timeout
        while len(received) < until_count:
            if asyncio.get_event_loop().time() > deadline:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_new_headlines_reach_the_handler():
    received = []
    engine = NewsEngine(on_headline=received.append)
    await engine.queue.put(make_headline("Story one"))
    await engine.queue.put(make_headline("Story two"))
    await _run_consumer(engine, 2, received)
    assert [h.title for h in received] == ["Story one", "Story two"]


async def test_duplicate_titles_are_dropped():
    received = []
    engine = NewsEngine(on_headline=received.append)
    await engine.queue.put(make_headline("Same story", source="CNBC"))
    await engine.queue.put(make_headline("same  STORY", source="Reuters"))
    await _run_consumer(engine, 2, received, timeout=0.3)
    assert len(received) == 1


async def test_stale_headlines_dropped_when_max_age_set():
    received = []
    engine = NewsEngine(on_headline=received.append, max_age=10)
    await engine.queue.put(make_headline("Old", ts_published=time.time() - 100))
    await engine.queue.put(make_headline("Fresh", ts_published=time.time()))
    await _run_consumer(engine, 1, received, timeout=0.3)
    assert [h.title for h in received] == ["Fresh"]


async def test_async_handler_is_awaited():
    received = []

    async def handler(headline):
        await asyncio.sleep(0)
        received.append(headline)

    engine = NewsEngine(on_headline=handler)
    await engine.queue.put(make_headline("Async story"))
    await _run_consumer(engine, 1, received)
    assert len(received) == 1


async def test_handler_exception_does_not_stop_pipeline():
    received = []

    def handler(headline):
        if headline.title == "boom":
            raise RuntimeError("handler failed")
        received.append(headline)

    engine = NewsEngine(on_headline=handler)
    await engine.queue.put(make_headline("boom"))
    await engine.queue.put(make_headline("after"))
    await _run_consumer(engine, 1, received)
    assert [h.title for h in received] == ["after"]


def test_active_names_reflect_enabled_sources(monkeypatch):
    from telltape import poller as poller_mod
    from telltape.models import FeedSource

    # Avoid spawning real poll tasks / network.
    monkeypatch.setattr(poller_mod.FeedPoller, "start", lambda self, src: None)
    monkeypatch.setattr(poller_mod.FeedPoller, "stop", lambda self, name: None)

    engine = NewsEngine(on_headline=lambda h: None)
    engine.enable(FeedSource("CNBC", "u"))
    engine.enable(FeedSource("NPR", "u"))
    assert engine.active_names == {"CNBC", "NPR"}
    engine.disable("CNBC")
    assert engine.active_names == {"NPR"}
