"""Tests for headline deduplication."""

from __future__ import annotations

from telltape.dedup import Deduper


def test_first_sighting_is_new():
    d = Deduper()
    assert d.is_new("fed holds rates steady") is True


def test_exact_duplicate_is_not_new():
    d = Deduper()
    d.is_new("fed holds rates steady")
    assert d.is_new("fed holds rates steady") is False


def test_fuzzy_near_duplicate_is_caught():
    d = Deduper(threshold=80.0)
    assert d.is_new("apple recalls some units in europe") is True
    # Same story, reworded: a high token_set_ratio collapses it.
    assert d.is_new("apple recalls some units across europe") is False


def test_threshold_zero_disables_fuzzy_matching():
    d = Deduper(threshold=0.0)
    assert d.is_new("apple recalls some units in europe") is True
    assert d.is_new("apple recalls some units across europe") is True


def test_unrelated_titles_are_each_new():
    d = Deduper(threshold=88.0)
    assert d.is_new("oil prices climb on supply fears") is True
    assert d.is_new("fed signals one more rate cut") is True


def test_capacity_eviction_forgets_oldest_exact_title():
    d = Deduper(capacity=2, threshold=0.0)
    d.is_new("alpha")
    d.is_new("bravo")
    assert d.is_new("charlie") is True  # evicts "alpha", leaving {bravo, charlie}
    assert d.is_new("bravo") is False  # still remembered
    assert d.is_new("charlie") is False  # still remembered
    assert d.is_new("alpha") is True  # was evicted, so new again


def test_reseeing_exact_refreshes_recency():
    d = Deduper(capacity=2, threshold=0.0)
    d.is_new("alpha")
    d.is_new("bravo")
    d.is_new("alpha")  # refreshes alpha to most-recent
    d.is_new("charlie")  # evicts bravo, not alpha
    assert d.is_new("alpha") is False
    assert d.is_new("bravo") is True
