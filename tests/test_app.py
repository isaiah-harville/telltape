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
        app.screen.query_one("#alerts", Input).value = "AAPL, war"
        app.screen.query_one("#alerts_sound", Checkbox).value = False
        await pilot.click("#save")
        await pilot.pause()
        assert app.alerts.terms == ["AAPL", "war"]
        assert app.config.alerts_sound is False


async def test_open_settings_and_save(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        app.screen.query_one("#keyword", Input).value = "war"
        app.screen.query_one("#vim_keys", Checkbox).value = True
        # Save sits below the fold in a small viewport; press it directly.
        app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert app.settings["keyword"] == "war"
        assert app.config.vim_keys is True


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
