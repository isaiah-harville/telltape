"""Shared fixtures.

Every test runs with the application's base directory redirected into a tmp
path, so no test reads or writes the real ``~/.telltape``. Network access is
never required: tests that need a company table build one in memory.
"""

from __future__ import annotations

import pytest

from telltape import paths
from telltape.companies import Company, CompanyTable
from telltape.models import NEWS, WORLD, FeedSource, Headline


@pytest.fixture(autouse=True)
def app_dir(tmp_path, monkeypatch):
    """Redirect ``paths.base_dir`` to an isolated tmp directory."""
    target = tmp_path / "telltape-home"
    target.mkdir()
    monkeypatch.setattr(paths, "base_dir", lambda: target)
    return target


@pytest.fixture
def company_table() -> CompanyTable:
    """A small in-memory company table for resolution and mention tests."""
    return CompanyTable(
        [
            Company("AAPL", "Apple Inc.", "apple"),
            Company("TSLA", "Tesla, Inc.", "tesla"),
            Company("MSFT", "Microsoft Corporation", "microsoft"),
            Company("NVDA", "NVIDIA Corporation", "nvidia"),
        ]
    )


@pytest.fixture
def tui_env(monkeypatch):
    """Neutralize network for TUI tests: no polling, no company download."""
    from telltape import poller as poller_mod

    monkeypatch.setattr(poller_mod.FeedPoller, "start", lambda self, src: None)
    monkeypatch.setattr(poller_mod.FeedPoller, "stop", lambda self, name: None)
    monkeypatch.setattr(
        CompanyTable, "load", classmethod(lambda cls, **kwargs: cls([]))
    )


@pytest.fixture
def host_app(tui_env):
    """A minimal configured app for mounting and exercising modal screens."""
    from telltape.config import Config, save_config
    from telltape.tui.app import TelltapeApp

    save_config(Config(contact_email="host@x.com"))
    return TelltapeApp(sources=[FeedSource("CNBC", "https://x/1", group="Wires")])


@pytest.fixture
def sample_sources() -> list[FeedSource]:
    """A compact source set with mixed groups and default_on states."""
    return [
        FeedSource("CNBC", "https://x/1", group="Wires"),
        FeedSource("NPR", "https://x/2", category=WORLD, group="World"),
        FeedSource("EDGAR 8-K", "https://x/3", group="SEC Filings", default_on=False),
    ]


def make_headline(
    title: str = "Example headline",
    *,
    source: str = "Test Wire",
    url: str = "https://example.com/a",
    summary: str = "",
    category: str = NEWS,
    ts_published: float | None = None,
    tickers: tuple[str, ...] = (),
) -> Headline:
    """Build a Headline with sensible defaults for tests."""
    return Headline(
        source=source,
        title=title,
        url=url,
        summary=summary,
        category=category,
        ts_published=ts_published,
        tickers=tickers,
    )
