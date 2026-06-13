"""Tests for the settings screen's parsing and theme preview."""

from __future__ import annotations

from textual.widgets import Button, Checkbox, Input, Select

from telltape.tui.settings import SettingsScreen


def _settings(**over) -> SettingsScreen:
    base = dict(
        contact_email="a@b.com",
        max_age=None,
        theme="nord",
        vim_keys=False,
        source_names=["CNBC", "NPR"],
        key_bindings={},
    )
    base.update(over)
    return SettingsScreen(**base)


async def test_save_parses_values(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_settings(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        host_app.screen.query_one("#max_age", Input).value = "600"
        host_app.screen.query_one("#vim_keys", Checkbox).value = True
        host_app.screen.query_one("#save", Button).press()
        await pilot.pause()
        v = result["v"]
        assert v["max_age"] == 600.0
        assert v["vim_keys"] is True
        # Watchlist and keyword moved to the Alerts screen.
        assert "filters" not in v
        assert "keyword" not in v


async def test_blank_max_age_is_none(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_settings(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        host_app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert result["v"]["max_age"] is None


async def test_invalid_max_age_is_none(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_settings(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        host_app.screen.query_one("#max_age", Input).value = "not-a-number"
        host_app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert result["v"]["max_age"] is None


async def test_key_bindings_collected(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_settings(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        host_app.screen.query_one("#kb_1", Select).value = "CNBC"
        host_app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert result["v"]["key_bindings"]["1"] == "CNBC"


async def test_cancel_reverts_theme_preview(host_app):
    async with host_app.run_test() as pilot:
        await pilot.pause()
        original = host_app.theme
        host_app.push_screen(_settings(theme=original))
        await pilot.pause()
        other = next(t for t in host_app.available_themes if t != original)
        host_app.screen.query_one("#theme", Select).value = other
        await pilot.pause()
        assert host_app.theme == other  # live preview applied
        host_app.screen.query_one("#cancel", Button).press()
        await pilot.pause()
        assert host_app.theme == original  # reverted on cancel
