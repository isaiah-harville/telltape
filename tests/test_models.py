"""Tests for core data types."""

from __future__ import annotations

import time

import pytest

from telltape.models import FILING, NEWS, WORLD, FeedSource, Headline

from .conftest import make_headline


def test_feedsource_defaults():
    src = FeedSource("CNBC", "https://example.com/rss")
    assert src.category == NEWS
    assert src.group == ""
    assert src.interval == 15.0
    assert src.default_on is True
    assert src.headers == {}


def test_feedsource_is_frozen():
    import dataclasses

    src = FeedSource("A", "u", group="Wires")
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(src, "name", "B")


def test_feedsource_equality():
    assert FeedSource("A", "u", group="Wires") == FeedSource("A", "u", group="Wires")
    assert FeedSource("A", "u") != FeedSource("A", "u", group="Wires")


def test_normalized_title_lowercases_and_collapses_whitespace():
    h = make_headline("  Fed   HOLDS\trates  Steady ")
    assert h.normalized_title == "fed holds rates steady"


def test_same_story_across_wires_shares_id():
    a = make_headline("Apple recalls some units", source="CNBC")
    b = make_headline("apple  recalls   some units", source="Reuters")
    # The id intentionally ignores source and URL so cross-posts collapse.
    assert a.id == b.id


def test_different_titles_have_different_ids():
    assert make_headline("Stocks rise").id != make_headline("Stocks fall").id


def test_age_none_when_unpublished():
    assert make_headline(ts_published=None).age is None


def test_age_is_seconds_since_publication():
    h = make_headline(ts_published=time.time() - 120)
    assert h.age is not None
    assert 115 <= h.age <= 130


def test_age_never_negative_for_future_timestamps():
    h = make_headline(ts_published=time.time() + 1000)
    assert h.age == 0.0


def test_category_constants_are_distinct():
    assert len({NEWS, WORLD, FILING}) == 3


def test_headline_default_fetched_is_now():
    before = time.time()
    h = Headline(source="s", title="t", url="u")
    assert before <= h.ts_fetched <= time.time() + 1
