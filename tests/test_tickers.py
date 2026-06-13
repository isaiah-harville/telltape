"""Tests for cashtag extraction."""

from __future__ import annotations

from telltape.tickers import extract_tickers


def test_extracts_simple_cashtag():
    assert extract_tickers("Buy $AAPL now") == ("AAPL",)


def test_preserves_first_seen_order_and_dedupes():
    assert extract_tickers("$TSLA $AAPL $TSLA") == ("TSLA", "AAPL")


def test_dedupes_across_multiple_texts():
    assert extract_tickers("$AAPL up", "more on $AAPL") == ("AAPL",)


def test_ignores_dollar_amounts():
    assert extract_tickers("priced at $50 today") == ()


def test_lookbehind_rejects_cashtag_inside_token():
    assert extract_tickers("abc$XYZ") == ()


def test_allows_class_suffix():
    assert extract_tickers("$BRK.A and $RDS-B") == ("BRK", "RDS")


def test_rejects_lowercase():
    assert extract_tickers("$apple") == ()


def test_caps_symbol_length_at_five():
    # Six letters: the engine matches the first five, leaving a trailing letter.
    assert extract_tickers("$ABCDEFG") == ()


def test_handles_empty_and_none_safely():
    assert extract_tickers("", None) == ()
