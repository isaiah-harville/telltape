"""Integration tests for the Textual application.

These drive the real app through a headless pilot. Network is stubbed out by
the ``tui_env`` fixture, and a contact email is pre-seeded so the first-run
contact dialog does not appear.
"""

from __future__ import annotations

import pytest
from textual.widgets import Button, Checkbox, Input, SelectionList

from telltape.config import Config, save_config
from telltape.tui.alerts import AlertsScreen
from telltape.tui.app import TelltapeApp
from telltape.tui.catalog import SourceCatalogScreen
from telltape.tui.settings import SettingsScreen


@pytest.fixture
def app(tui_env, sample_sources):
    save_config(Config(contact_email="trader@x.com"))
    return TelltapeApp(sources=sample_sources)


async def test_app_boots_without_contact_screen(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen_stack[-1] is app.screen  # no modal pushed
        sl = app.query_one("#sources", SelectionList)
        assert sl.option_count == 3


async def test_default_on_sources_start_enabled(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        # CNBC and NPR default on; EDGAR 8-K default off.
        assert set(sl.selected) == {"CNBC", "NPR"}


async def test_number_key_toggles_source(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        assert "CNBC" in sl.selected
        await pilot.press("1")  # first source -> CNBC
        await pilot.pause()
        assert "CNBC" not in sl.selected


async def test_all_and_no_sources_bindings(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        await pilot.press("A")
        await pilot.pause()
        assert set(sl.selected) == {"CNBC", "NPR", "EDGAR 8-K"}
        await pilot.press("X")
        await pilot.pause()
        assert set(sl.selected) == set()


async def test_toggling_sources_drives_the_engine(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("A")
        await pilot.pause()
        assert app.engine.active_names == {"CNBC", "NPR", "EDGAR 8-K"}
        await pilot.press("X")
        await pilot.pause()
        assert app.engine.active_names == set()


async def test_pause_resume_binding(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.paused is False
        await pilot.press("t")
        assert app.paused is True
        await pilot.press("t")
        assert app.paused is False


async def test_clear_tape(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app._tape.write("a line")
        app.action_clear_tape()
        # A cleared RichLog has no retained lines.
        assert app._tape.lines == []


async def test_vim_keys_route_to_panes(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.config.vim_keys = True
        sl = app.query_one("#sources", SelectionList)
        sl.focus()
        await pilot.pause()
        assert app._handle_vim_key("j") is True  # cursor in source list
        app.set_focus(None)
        assert app._handle_vim_key("j") is True  # scrolls the tape
        assert app._handle_vim_key("z") is False  # not a vim key


async def test_open_alerts_and_save(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert isinstance(app.screen, AlertsScreen)
        app.screen.query_one("#watchlist", Input).value = "Tesla"
        app.screen.query_one("#keyword", Input).value = "war"
        app.screen.query_one("#alerts", Input).value = "AAPL, war"
        app.screen.query_one("#alerts_sound", Checkbox).value = False
        app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert app.alerts.terms == ["AAPL", "war"]
        assert app.watchlist.terms == ["Tesla"]
        assert app.settings["keyword"] == "war"
        assert app.config.alerts_sound is False


async def test_alert_config_persists_across_restart(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        app.screen.query_one("#watchlist", Input).value = "Tesla, oil"
        app.screen.query_one("#keyword", Input).value = "war"
        app.screen.query_one("#alerts", Input).value = "AAPL, recall"
        app.screen.query_one("#save", Button).press()
        await pilot.pause()

    # A fresh app instance reads the same on-disk config (same tmp app dir).
    from telltape.tui.app import TelltapeApp

    restarted = TelltapeApp(sources=app.sources)
    assert restarted.config.watchlist == ["Tesla", "oil"]
    assert restarted.config.keyword == "war"
    assert restarted.config.alerts == ["AAPL", "recall"]
    assert restarted.watchlist.terms == ["Tesla", "oil"]
    assert restarted.alerts.terms == ["AAPL", "recall"]
    assert restarted.settings["keyword"] == "war"


async def test_enabled_sources_persist_across_restart(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("A")  # all on, incl. EDGAR 8-K (default off)
        await pilot.pause()
        assert set(app.config.enabled_sources) == {"CNBC", "NPR", "EDGAR 8-K"}

    restarted = TelltapeApp(sources=app.sources)
    async with restarted.run_test() as pilot:
        await pilot.pause()
        sl = restarted.query_one("#sources", SelectionList)
        # Restored from config, not from each source's default_on.
        assert set(sl.selected) == {"CNBC", "NPR", "EDGAR 8-K"}
        assert restarted.engine.active_names == {"CNBC", "NPR", "EDGAR 8-K"}


async def test_disabling_all_sources_persists_as_empty(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("X")  # all off
        await pilot.pause()
        assert app.config.enabled_sources == []

    restarted = TelltapeApp(sources=app.sources)
    async with restarted.run_test() as pilot:
        await pilot.pause()
        sl = restarted.query_one("#sources", SelectionList)
        assert set(sl.selected) == set()


async def test_open_settings_and_save(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        app.screen.query_one("#vim_keys", Checkbox).value = True
        # Save sits below the fold in a small viewport; press it directly.
        app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert app.config.vim_keys is True


async def test_source_rows_show_columns(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        prompt = sl.get_option_at_index(0).prompt
        text = prompt if isinstance(prompt, str) else prompt.plain
        # The first source is CNBC (news / Wires).
        assert "CNBC" in text
        assert "news" in text
        assert "Wires" in text


async def test_save_email_button_persists_without_closing(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#contact", Input).value = "new@x.com"
        app.screen.query_one("#save_email", Button).press()
        await pilot.pause()
        assert app.config.contact_email == "new@x.com"
        assert isinstance(app.screen, SettingsScreen)  # dialog stays open


async def test_invalid_email_is_not_saved(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#contact", Input).value = "not-an-email"
        app.screen.query_one("#save_email", Button).press()
        await pilot.pause()
        assert app.config.contact_email == "trader@x.com"  # unchanged


async def test_main_save_does_not_change_email(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        app.screen.query_one("#contact", Input).value = "changed@x.com"
        app.screen.query_one("#save", Button).press()  # main Save
        await pilot.pause()
        # Email is saved only by its own button, never by the main Save.
        assert app.config.contact_email == "trader@x.com"


async def test_open_catalog_enable_all_and_save(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert isinstance(app.screen, SourceCatalogScreen)
        await pilot.click("#cat-all")
        await pilot.click("#cat-save")
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        assert set(sl.selected) == {"CNBC", "NPR", "EDGAR 8-K"}


async def test_catalog_cancel_leaves_sources_unchanged(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        sl = app.query_one("#sources", SelectionList)
        before = set(sl.selected)
        await pilot.press("b")
        await pilot.pause()
        await pilot.click("#cat-all")
        await pilot.click("#cat-cancel")
        await pilot.pause()
        assert set(sl.selected) == before
