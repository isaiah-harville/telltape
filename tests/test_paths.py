"""Tests for filesystem path helpers."""

from __future__ import annotations

from telltape import paths


def test_app_name():
    assert paths.APP_NAME == "telltape"


def test_config_file_under_base_dir(app_dir):
    assert paths.config_file() == app_dir / "config.toml"


def test_feeds_file_under_base_dir(app_dir):
    assert paths.feeds_file() == app_dir / "feeds.toml"


def test_cache_file_named_under_base_dir(app_dir):
    assert paths.cache_file("company_tickers.json") == app_dir / "company_tickers.json"


def test_all_paths_share_the_base_dir(app_dir):
    for p in (paths.config_file(), paths.feeds_file(), paths.cache_file("x.json")):
        assert p.parent == app_dir
