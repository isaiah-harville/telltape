"""Tests for watchlist filtering."""

from __future__ import annotations

from telltape.watchlist import Watchlist

from .conftest import make_headline


def test_empty_watchlist_matches_everything():
    wl = Watchlist()
    assert wl.active is False
    assert wl.matches(make_headline("anything at all")) is True


def test_text_term_matches_title_case_insensitively():
    wl = Watchlist(["oil"])
    assert wl.active is True
    assert wl.matches(make_headline("OIL slips on supply")) is True
    assert wl.matches(make_headline("stocks rally")) is False


def test_ticker_term_matches_detected_cashtag(company_table):
    wl = Watchlist(["AAPL"], table=company_table)
    assert wl.matches(make_headline("Apple news", tickers=("AAPL",))) is True
    assert wl.matches(make_headline("Tesla news", tickers=("TSLA",))) is False


def test_company_name_term_matches_mention_in_title(company_table):
    wl = Watchlist(["Tesla"], table=company_table)
    # No cashtag, no ticker tuple — resolved via the company name in the title.
    assert wl.matches(make_headline("Tesla unveils new model")) is True
    assert wl.matches(make_headline("Apple unveils new phone")) is False


def test_set_table_upgrades_text_term_to_ticker(company_table):
    wl = Watchlist(["Tesla"])
    # Before a table, "Tesla" is a plain text term.
    assert wl.matches(make_headline("article about tesla cars")) is True
    wl.set_table(company_table)
    # After, it resolves to TSLA and matches the company mention.
    assert wl.matches(make_headline("Tesla earnings beat")) is True


def test_set_terms_recompiles():
    wl = Watchlist(["oil"])
    wl.set_terms(["gold"])
    assert wl.matches(make_headline("gold hits record")) is True
    assert wl.matches(make_headline("oil dips")) is False


def test_terms_property_returns_copy():
    wl = Watchlist(["a", "b"])
    got = wl.terms
    got.append("c")
    assert wl.terms == ["a", "b"]
