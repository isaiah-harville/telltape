"""Tests for the source catalog screen."""

from __future__ import annotations

from textual.widgets import Input, SelectionList

from telltape.models import WORLD, FeedSource
from telltape.tui.catalog import SourceCatalogScreen


def _sources() -> list[FeedSource]:
    return [
        FeedSource("CNBC", "u1", group="Wires"),
        FeedSource("Benzinga", "u2", group="Wires"),
        FeedSource("NPR", "u3", category=WORLD, group="World"),
        FeedSource("EDGAR 8-K", "u4", group="SEC Filings"),
    ]


async def test_groups_render_one_list_each(host_app):
    async with host_app.run_test() as pilot:
        await pilot.pause()
        screen = SourceCatalogScreen(sources=_sources(), enabled={"CNBC"})
        await host_app.push_screen(screen)
        await pilot.pause()
        # Three groups: Wires, World, SEC Filings.
        assert len(screen.query(SelectionList)) == 3


async def test_search_filters_to_matching_group(host_app):
    async with host_app.run_test() as pilot:
        await pilot.pause()
        screen = SourceCatalogScreen(sources=_sources(), enabled=set())
        await host_app.push_screen(screen)
        await pilot.pause()
        screen.query_one("#catalog-search", Input).value = "edgar"
        await pilot.pause()
        lists = screen.query(SelectionList)
        assert len(lists) == 1


async def test_save_returns_enabled_set(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        screen = SourceCatalogScreen(sources=_sources(), enabled=set())
        host_app.push_screen(screen, lambda r: result.__setitem__("v", r))
        await pilot.pause()
        await pilot.click("#cat-all")
        await pilot.click("#cat-save")
        await pilot.pause()
        assert result["v"] == {"CNBC", "Benzinga", "NPR", "EDGAR 8-K"}


async def test_cancel_returns_none(host_app):
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        screen = SourceCatalogScreen(sources=_sources(), enabled={"CNBC"})
        host_app.push_screen(screen, lambda r: result.__setitem__("v", r))
        await pilot.pause()
        await pilot.click("#cat-all")
        await pilot.click("#cat-cancel")
        await pilot.pause()
        assert result["v"] is None


async def test_selection_survives_a_search(host_app):
    """A toggle made before searching is preserved through the search rebuild."""
    result = {}
    async with host_app.run_test() as pilot:
        await pilot.pause()
        screen = SourceCatalogScreen(sources=_sources(), enabled=set())
        host_app.push_screen(screen, lambda r: result.__setitem__("v", r))
        await pilot.pause()
        await pilot.click("#cat-all")  # enable everything
        # Narrow the view so most lists are unmounted, then save.
        screen.query_one("#catalog-search", Input).value = "cnbc"
        await pilot.pause()
        await pilot.click("#cat-save")
        await pilot.pause()
        # Hidden selections were harvested, not lost.
        assert result["v"] == {"CNBC", "Benzinga", "NPR", "EDGAR 8-K"}
