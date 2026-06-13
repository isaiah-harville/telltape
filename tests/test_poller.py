"""Tests for asynchronous feed polling."""

from __future__ import annotations

import asyncio
import calendar
import time

import httpx

from telltape.models import FILING, FeedSource
from telltape.poller import FeedPoller

RSS_TEMPLATE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test</title>
{items}
</channel></rss>"""

ITEM = """<item>
<title>{title}</title>
<link>{link}</link>
<description>{desc}</description>
<pubDate>{date}</pubDate>
</item>"""


def _rss(*items: str) -> str:
    return RSS_TEMPLATE.format(items="\n".join(items))


def _item(
    title="Headline", link="https://x/a", desc="", date="Tue, 10 Jun 2025 10:00:00 GMT"
) -> str:
    return ITEM.format(title=title, link=link, desc=desc, date=date)


# --- _to_headline -----------------------------------------------------------


def test_to_headline_maps_fields():
    entry = {
        "title": "  Big news  ",
        "link": "https://x/a",
        "summary": " body $AAPL ",
        "published_parsed": time.gmtime(1_700_000_000),
    }
    h = FeedPoller._to_headline(FeedSource("S", "u", category=FILING), entry, 123.0)
    assert h is not None
    assert h.title == "Big news"
    assert h.url == "https://x/a"
    assert h.summary == "body $AAPL"
    assert h.category == FILING
    assert h.source == "S"
    assert h.ts_fetched == 123.0
    assert h.ts_published == float(calendar.timegm(entry["published_parsed"]))
    assert h.tickers == ("AAPL",)


def test_to_headline_returns_none_without_title():
    assert FeedPoller._to_headline(FeedSource("S", "u"), {"title": "  "}, 1.0) is None


def test_to_headline_falls_back_to_updated_time():
    entry = {"title": "x", "updated_parsed": time.gmtime(1_650_000_000)}
    h = FeedPoller._to_headline(FeedSource("S", "u"), entry, 1.0)
    assert h.ts_published == float(calendar.timegm(entry["updated_parsed"]))


def test_to_headline_handles_missing_timestamp():
    h = FeedPoller._to_headline(FeedSource("S", "u"), {"title": "x"}, 1.0)
    assert h.ts_published is None


# --- _poll_once with a mock transport ---------------------------------------


def _poller_with(handler) -> tuple[FeedPoller, asyncio.Queue]:
    queue: asyncio.Queue = asyncio.Queue()
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return FeedPoller(queue, client=client), queue


async def test_poll_once_enqueues_new_entries():
    body = _rss(_item("First", "https://x/1"), _item("Second", "https://x/2"))

    def handler(request):
        return httpx.Response(200, text=body, headers={"ETag": "abc"})

    poller, queue = _poller_with(handler)
    src = FeedSource("Test", "https://feed/rss")
    await poller._poll_once(src)
    titles = {queue.get_nowait().title for _ in range(queue.qsize() or 2)}
    assert {"First", "Second"} <= titles
    assert poller._etag["https://feed/rss"] == "abc"
    await poller.aclose()


async def test_poll_once_sends_conditional_headers_and_handles_304():
    seen = {}

    def handler(request):
        seen["inm"] = request.headers.get("If-None-Match")
        return httpx.Response(304)

    poller, queue = _poller_with(handler)
    src = FeedSource("Test", "https://feed/rss")
    poller._etag[src.url] = "etag-1"
    await poller._poll_once(src)
    assert seen["inm"] == "etag-1"
    assert queue.empty()  # 304 yields nothing
    await poller.aclose()


async def test_start_and_stop_track_active_sources():
    def handler(request):
        return httpx.Response(200, text=_rss(_item()))

    poller, _ = _poller_with(handler)
    src = FeedSource("Test", "https://feed/rss", interval=0.01)
    poller.start(src)
    assert poller.active == {"Test"}
    poller.start(src)  # idempotent
    assert poller.active == {"Test"}
    poller.stop("Test")
    await asyncio.sleep(0)
    assert poller.active == set()
    await poller.aclose()


def test_set_user_agent_updates_client_header():
    queue: asyncio.Queue = asyncio.Queue()
    client = httpx.AsyncClient()
    poller = FeedPoller(queue, client=client, user_agent="old")
    poller.set_user_agent("telltape/0.1 me@x.com")
    assert client.headers["User-Agent"] == "telltape/0.1 me@x.com"
