"""Tests for feed source loading and on-disk configuration."""

from __future__ import annotations

from telltape import paths
from telltape.feeds import (
    DEFAULT_FEEDS,
    _parse,
    _render_toml,
    load_feeds,
    write_default_feeds,
)
from telltape.models import FILING, NEWS, WORLD


def test_defaults_cover_expected_groups():
    groups = {f.group for f in DEFAULT_FEEDS}
    assert {"Wires", "Crypto", "Macro & Policy", "SEC Filings", "World"} <= groups


def test_every_default_has_a_group():
    assert all(f.group for f in DEFAULT_FEEDS)


def test_high_volume_filings_start_disabled():
    by_name = {f.name: f for f in DEFAULT_FEEDS}
    assert by_name["EDGAR Form 4"].default_on is False
    assert by_name["EDGAR 8-K"].default_on is True


def test_first_load_seeds_file_and_returns_defaults():
    target = paths.feeds_file()
    assert not target.exists()
    feeds, error = load_feeds()
    assert error is None
    assert target.exists()
    assert [f.name for f in feeds] == [f.name for f in DEFAULT_FEEDS]


def test_round_trip_preserves_group_and_fields():
    target = paths.feeds_file()
    write_default_feeds(target)
    feeds, error = load_feeds(target)
    assert error is None
    original = {f.name: f for f in DEFAULT_FEEDS}
    for f in feeds:
        src = original[f.name]
        assert f.group == src.group
        assert f.category == src.category
        assert f.default_on == src.default_on
        assert f.interval == src.interval


def test_render_toml_emits_group():
    toml = _render_toml(DEFAULT_FEEDS)
    assert 'group = "Crypto"' in toml
    assert "# category must be one of" in toml


def test_parse_skips_rows_missing_name_or_url():
    data = {
        "feed": [
            {"name": "Good", "url": "https://x"},
            {"name": "", "url": "https://y"},
            {"name": "NoUrl"},
            "not a dict",
        ]
    }
    feeds = _parse(data)
    assert [f.name for f in feeds] == ["Good"]


def test_parse_defaults_unknown_category_to_news():
    feeds = _parse({"feed": [{"name": "X", "url": "u", "category": "bogus"}]})
    assert feeds[0].category == NEWS


def test_parse_accepts_known_categories():
    feeds = _parse(
        {
            "feed": [
                {"name": "W", "url": "u", "category": WORLD},
                {"name": "F", "url": "u", "category": FILING},
            ]
        }
    )
    assert [f.category for f in feeds] == [WORLD, FILING]


def test_parse_bad_interval_falls_back():
    feeds = _parse({"feed": [{"name": "X", "url": "u", "interval": "soon"}]})
    assert feeds[0].interval == 15.0


def test_parse_reads_group_and_headers():
    feeds = _parse(
        {
            "feed": [
                {
                    "name": "X",
                    "url": "u",
                    "group": "Crypto",
                    "headers": {"Authorization": "Bearer t"},
                }
            ]
        }
    )
    assert feeds[0].group == "Crypto"
    assert feeds[0].headers == {"Authorization": "Bearer t"}


def test_load_invalid_toml_returns_defaults_with_message():
    paths.feeds_file().write_text("= = =")
    feeds, error = load_feeds()
    assert [f.name for f in feeds] == [f.name for f in DEFAULT_FEEDS]
    assert error is not None


def test_load_empty_feeds_returns_defaults_with_message():
    paths.feeds_file().write_text("# nothing here\n")
    feeds, error = load_feeds()
    assert [f.name for f in feeds] == [f.name for f in DEFAULT_FEEDS]
    assert error is not None
    assert "No valid feeds" in error


def test_write_default_feeds_creates_parent_dirs(tmp_path):
    nested = tmp_path / "a" / "b" / "feeds.toml"
    write_default_feeds(nested)
    assert nested.exists()
