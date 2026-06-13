"""Tests for headline rendering."""

from __future__ import annotations

import time

from rich.style import Style

from telltape.models import FILING
from telltape.render import _age_str, format_headline

from .conftest import make_headline


def test_age_str_unknown():
    assert _age_str(make_headline(ts_published=None)).strip() == "--"


def test_age_str_seconds():
    assert _age_str(make_headline(ts_published=time.time() - 5)).strip() == "5s"


def test_age_str_minutes():
    assert _age_str(make_headline(ts_published=time.time() - 120)).strip() == "2m"


def test_age_str_hours_and_minutes():
    # 2 hours 5 minutes -> "2h05m", not just "2h".
    assert _age_str(make_headline(ts_published=time.time() - 7500)).strip() == "2h05m"


def test_age_str_days_and_hours():
    # 3 days, 4 hours -> "3d04h".
    age = 3 * 86_400 + 4 * 3600 + 90
    assert _age_str(make_headline(ts_published=time.time() - age)).strip() == "3d04h"


def test_age_str_large_age_falls_back_to_days():
    # 200 days -> "200d" (no hours), still within the column.
    assert _age_str(make_headline(ts_published=time.time() - 200 * 86_400)).strip() == (
        "200d"
    )


def test_age_str_columns_are_fixed_width():
    now = time.time()
    ages = (
        None,
        now - 5,  # seconds
        now - 120,  # minutes
        now - 7500,  # hours+minutes
        now - 3 * 86_400,  # days+hours
        now - 200 * 86_400,  # days only
        now - 5000 * 86_400,  # very old
    )
    widths = {len(_age_str(make_headline(ts_published=t))) for t in ages}
    assert widths == {7}


def test_format_includes_source_and_title():
    text = format_headline(make_headline("Big news", source="CNBC")).plain
    assert "CNBC" in text
    assert "Big news" in text


def test_format_truncates_long_source_to_twenty():
    text = format_headline(make_headline(source="A" * 40)).plain
    assert "A" * 20 in text
    assert "A" * 21 not in text


def test_alert_adds_marker():
    assert format_headline(make_headline(), alert=True).plain.startswith("● ")


def test_non_alert_has_no_marker():
    assert not format_headline(make_headline()).plain.startswith("● ")


def test_tickers_appended_as_cashtags():
    text = format_headline(make_headline(tickers=("AAPL", "TSLA"))).plain
    assert "$AAPL" in text
    assert "$TSLA" in text


def test_keyword_highlight_creates_span():
    text = format_headline(make_headline("war breaks out"), keyword="war")
    assert any(s.style == "black on yellow" for s in text.spans)


def test_url_carried_as_meta_on_line():
    url = "https://example.com/story"
    text = format_headline(make_headline(url=url))
    assert any(
        isinstance(s.style, Style) and s.style.meta.get("url") == url
        for s in text.spans
    )


def test_no_meta_span_when_url_missing():
    text = format_headline(make_headline(url=""))
    assert not any(
        isinstance(s.style, Style) and s.style.meta.get("url") for s in text.spans
    )


def test_filing_category_styles_source():
    text = format_headline(make_headline(source="EDGAR 8-K", category=FILING))
    assert any("magenta" in str(s.style) for s in text.spans)
