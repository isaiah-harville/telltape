"""Tests for persistent settings."""

from __future__ import annotations

from telltape import paths
from telltape.config import DEFAULT_THEME, Config, load_config, save_config


def test_defaults():
    c = Config()
    assert c.contact_email == ""
    assert c.theme == DEFAULT_THEME
    assert c.alerts_sound is True
    assert c.fuzzy_threshold == 88.0
    assert c.vim_keys is False
    assert c.watchlist == []
    assert c.keyword == ""
    assert c.alerts == []
    assert c.key_bindings == {}


def test_user_agent_without_contact():
    assert Config().user_agent == "telltape/0.1"


def test_user_agent_with_contact():
    assert Config(contact_email="me@x.com").user_agent == "telltape/0.1 me@x.com"


def test_load_missing_file_returns_defaults():
    config, error = load_config()
    assert error is None
    assert config == Config()


def test_save_then_load_round_trip():
    original = Config(
        contact_email="trader@x.com",
        theme="gruvbox",
        alerts_sound=False,
        fuzzy_threshold=75.0,
        vim_keys=True,
        watchlist=["AAPL", "Tesla"],
        keyword="war",
        alerts=["recall", "bankruptcy"],
        key_bindings={"1": "CNBC Markets", "2": "EDGAR 8-K"},
    )
    save_config(original)
    loaded, error = load_config()
    assert error is None
    assert loaded == original


def test_alert_fields_round_trip_with_quoting():
    # Terms with commas/quotes must survive the TOML array round-trip.
    original = Config(watchlist=['a "quoted" name'], alerts=["x\\y"], keyword="war")
    save_config(original)
    loaded, error = load_config()
    assert error is None
    assert loaded.watchlist == ['a "quoted" name']
    assert loaded.alerts == ["x\\y"]
    assert loaded.keyword == "war"


def test_empty_alert_arrays_round_trip():
    save_config(Config())
    text = paths.config_file().read_text()
    assert "watchlist = []" in text
    assert "alerts = []" in text
    loaded, _ = load_config()
    assert loaded.watchlist == []
    assert loaded.alerts == []


def test_load_invalid_toml_returns_defaults_with_message():
    paths.config_file().write_text("this is = = not toml")
    config, error = load_config()
    assert config == Config()
    assert error is not None
    assert "using defaults" in error


def test_load_ignores_wrongly_typed_fields():
    paths.config_file().write_text(
        'contact_email = 5\ntheme = true\nvim_keys = "yes"\nfuzzy_threshold = "high"\n'
    )
    config, error = load_config()
    assert error is None
    # All bad types fall back to defaults rather than raising.
    assert config == Config()


def test_vim_keys_persisted_as_bool():
    save_config(Config(vim_keys=True))
    assert "vim_keys = true" in paths.config_file().read_text()
    save_config(Config(vim_keys=False))
    assert "vim_keys = false" in paths.config_file().read_text()


def test_key_bindings_section_only_written_when_present():
    save_config(Config())
    assert "[key_bindings]" not in paths.config_file().read_text()
    save_config(Config(key_bindings={"3": "NPR News"}))
    text = paths.config_file().read_text()
    assert "[key_bindings]" in text
    assert '3 = "NPR News"' in text
