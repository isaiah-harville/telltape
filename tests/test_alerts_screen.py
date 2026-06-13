"""Tests for the dedicated alerts screen."""

from __future__ import annotations

from textual.widgets import Button, Checkbox, Input

from telltape.tui.alerts import AlertsScreen


def _alerts(**over) -> AlertsScreen:
    base = dict(watchlist=[], keyword="", alerts=[], alerts_sound=True)
    base.update(over)
    return AlertsScreen(**base)


async def test_save_parses_all_fields(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(
            _alerts(alerts=["AAPL"]), lambda r: result.__setitem__("v", r)
        )
        await pilot.pause()
        host_app.screen.query_one("#watchlist", Input).value = "Tesla , oil "
        host_app.screen.query_one("#keyword", Input).value = "war"
        host_app.screen.query_one("#alerts", Input).value = " TSLA , recall , "
        host_app.screen.query_one("#alerts_sound", Checkbox).value = False
        host_app.screen.query_one("#save", Button).press()
        await pilot.pause()
        assert result["v"] == {
            "watchlist": ["Tesla", "oil"],
            "keyword": "war",
            "alerts": ["TSLA", "recall"],
            "alerts_sound": False,
        }


async def test_prefills_existing_values(host_app):
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(
            _alerts(watchlist=["AAPL", "Tesla"], keyword="war", alerts=["recall"])
        )
        await pilot.pause()
        assert host_app.screen.query_one("#watchlist", Input).value == "AAPL, Tesla"
        assert host_app.screen.query_one("#keyword", Input).value == "war"
        assert host_app.screen.query_one("#alerts", Input).value == "recall"


async def test_cancel_returns_none(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_alerts(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        host_app.screen.query_one("#cancel", Button).press()
        await pilot.pause()
        assert result["v"] is None


async def test_escape_cancels(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        host_app.push_screen(_alerts(), lambda r: result.__setitem__("v", r))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert result["v"] is None
