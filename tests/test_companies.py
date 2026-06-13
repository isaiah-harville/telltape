"""Tests for company resolution and the SEC table."""

from __future__ import annotations

import json
import time

import pytest

from telltape.companies import _CACHE_NAME, Company, CompanyTable, _core_name


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Tesla, Inc.", "tesla"),
        ("Microsoft Corporation", "microsoft"),
        ("The Goldman Sachs Group, Inc.", "goldman sachs"),
        ("Apple Inc.", "apple"),
        ("Ford Motor Company", "ford motor"),
    ],
)
def test_core_name_strips_suffixes_and_punctuation(name, expected):
    assert _core_name(name) == expected


def test_resolve_exact_ticker_is_case_insensitive(company_table):
    assert company_table.resolve("aapl").ticker == "AAPL"


def test_resolve_exact_core_name(company_table):
    assert company_table.resolve("Apple Inc.").ticker == "AAPL"


def test_resolve_fuzzy_with_relaxed_cutoff(company_table):
    assert company_table.resolve("Tesla Motors", score_cutoff=50).ticker == "TSLA"


def test_resolve_unknown_returns_none(company_table):
    assert company_table.resolve("Wingdings Unlimited LLC") is None


def test_resolve_blank_returns_none(company_table):
    assert company_table.resolve("   ") is None


def test_get_returns_company_or_none(company_table):
    assert company_table.get("nvda").ticker == "NVDA"
    assert company_table.get("ZZZZ") is None


def test_mentions_cashtag(company_table):
    assert company_table.mentions("buying $AAPL today", "AAPL") is True


def test_mentions_company_core_as_whole_word(company_table):
    assert company_table.mentions("Apple recalls units", "AAPL") is True


def test_mentions_requires_word_boundary(company_table):
    assert company_table.mentions("pineapple harvest", "AAPL") is False


def test_parse_skips_malformed_rows():
    payload = {
        "0": {"ticker": "AAPL", "title": "Apple Inc."},
        "1": {"ticker": "TSLA"},  # missing title
        "2": "garbage",
    }
    companies = CompanyTable._parse(payload)
    assert [c.ticker for c in companies] == ["AAPL"]


def test_load_reads_fresh_cache_without_network(tmp_path):
    cache = tmp_path / _CACHE_NAME
    cache.write_text(json.dumps({"0": {"ticker": "AAPL", "title": "Apple Inc."}}))
    table = CompanyTable.load(user_agent="t@x.com", cache_dir=str(tmp_path))
    company = table.get("AAPL")
    assert company is not None
    assert company.name == "Apple Inc."


def test_load_refreshes_via_download(monkeypatch, tmp_path):
    payload = {"0": {"ticker": "NVDA", "title": "NVIDIA Corporation"}}
    monkeypatch.setattr(
        CompanyTable, "_download", staticmethod(lambda ua, timeout: payload)
    )
    table = CompanyTable.load(
        user_agent="t@x.com", cache_dir=str(tmp_path), refresh=True
    )
    assert table.get("NVDA") is not None
    # Download result is cached for next time.
    assert (tmp_path / _CACHE_NAME).exists()


def test_load_ignores_stale_cache(monkeypatch, tmp_path):
    cache = tmp_path / _CACHE_NAME
    cache.write_text(json.dumps({"0": {"ticker": "OLD", "title": "Old Co"}}))
    # Backdate the cache well beyond the TTL.
    old = time.time() - 30 * 24 * 3600
    import os

    os.utime(cache, (old, old))
    payload = {"0": {"ticker": "NEW", "title": "New Co"}}
    monkeypatch.setattr(
        CompanyTable, "_download", staticmethod(lambda ua, timeout: payload)
    )
    table = CompanyTable.load(user_agent="t@x.com", cache_dir=str(tmp_path))
    assert table.get("NEW") is not None
    assert table.get("OLD") is None


def test_company_is_frozen():
    c = Company("AAPL", "Apple Inc.", "apple")
    with pytest.raises(Exception):
        setattr(c, "ticker", "X")
