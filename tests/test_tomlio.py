"""Tests for the minimal TOML quoting helper."""

from __future__ import annotations

import tomllib

from telltape.tomlio import quote


def test_plain_string():
    assert quote("hello") == '"hello"'


def test_escapes_double_quotes():
    assert quote('say "hi"') == '"say \\"hi\\""'


def test_escapes_backslashes():
    assert quote("a\\b") == '"a\\\\b"'


def test_round_trips_through_tomllib():
    for value in ["plain", 'with "quotes"', "back\\slash", "url?a=1&b=2", "café"]:
        doc = f"k = {quote(value)}"
        assert tomllib.loads(doc)["k"] == value
