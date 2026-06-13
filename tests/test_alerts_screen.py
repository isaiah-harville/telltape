"""Tests for the dedicated alerts screen."""

from __future__ import annotations

from textual.widgets import Checkbox, Input

from telltape.tui.alerts import AlertsScreen


async def test_save_parses_and_trims_terms(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(
            AlertsScreen(alerts=["AAPL"], alerts_sound=True),
            lambda r: result.__setitem__("v", r),
        )
        await pilot.pause()
        host_app.screen.query_one("#alerts", Input).value = " TSLA , recall , "
        host_app.screen.query_one("#alerts_sound", Checkbox).value = False
        await pilot.click("#save")
        await pilot.pause()
        assert result["v"] == {"alerts": ["TSLA", "recall"], "alerts_sound": False}


async def test_prefills_existing_terms(host_app):
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(AlertsScreen(alerts=["AAPL", "war"], alerts_sound=True))
        await pilot.pause()
        assert host_app.screen.query_one("#alerts", Input).value == "AAPL, war"


async def test_cancel_returns_none(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(
            AlertsScreen(alerts=[], alerts_sound=True),
            lambda r: result.__setitem__("v", r),
        )
        await pilot.pause()
        await pilot.click("#cancel")
        await pilot.pause()
        assert result["v"] is None


async def test_escape_cancels(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(
            AlertsScreen(alerts=[], alerts_sound=True),
            lambda r: result.__setitem__("v", r),
        )
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert result["v"] is None
