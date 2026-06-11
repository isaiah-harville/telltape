"""Company-to-ticker resolution backed by the SEC company list.

The SEC publishes a JSON file mapping ticker symbols to company names. This
module downloads and caches that file, resolves a user query (a ticker or a
company name) to a canonical company, and detects company mentions in free text.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from rapidfuzz import fuzz, process

from .paths import cache_file

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_CACHE_TTL_SECONDS = 7 * 24 * 3600
_CACHE_NAME = "company_tickers.json"

# Common corporate suffixes and stop words removed when reducing a company name
# to a matchable core.
_SUFFIX_RE = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|companies|co|ltd|limited|"
    r"llc|plc|lp|holdings|holding|group|the|sa|ag|nv|se|trust)\b",
    re.IGNORECASE,
)
_NON_WORD_RE = re.compile(r"[^a-z0-9 ]+")


def _core_name(name: str) -> str:
    """Reduce a company name to a lowercase core for matching.

    Punctuation and common corporate suffixes are removed so that, for example,
    "Tesla, Inc." becomes "tesla".

    Args:
        name: Full company name.

    Returns:
        The simplified core name, which may be empty.
    """
    text = _NON_WORD_RE.sub(" ", name.lower())
    text = _SUFFIX_RE.sub(" ", text)
    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class Company:
    """A company resolved from the SEC list.

    Attributes:
        ticker: Upper-case stock symbol.
        name: Full company name as published by the SEC.
        core: Simplified name used for text matching.
    """

    ticker: str
    name: str
    core: str


class CompanyTable:
    """An indexed set of companies for resolution and mention detection."""

    def __init__(self, companies: list[Company]) -> None:
        """Initialize the table.

        Args:
            companies: Companies to index.
        """
        self._companies = companies
        self._by_ticker = {c.ticker: c for c in companies}
        self._cores = [c.core for c in companies]
        self._by_core: dict[str, Company] = {}
        for c in companies:
            self._by_core.setdefault(c.core, c)
        self._mention_cache: dict[str, re.Pattern[str]] = {}

    @classmethod
    def load(
        cls,
        *,
        user_agent: str,
        cache_dir: str | None = None,
        refresh: bool = False,
        timeout: float = 15.0,
    ) -> CompanyTable:
        """Load the table from the local cache or download it from the SEC.

        Args:
            user_agent: Contact User-Agent required by the SEC.
            cache_dir: Override for the cache directory.
            refresh: Force a re-download even if a fresh cache exists.
            timeout: HTTP timeout in seconds.

        Returns:
            A populated table.

        Raises:
            httpx.HTTPError: If a download is required and fails.
        """
        path = Path(cache_dir) / _CACHE_NAME if cache_dir else cache_file(_CACHE_NAME)
        data = None if refresh else cls._read_cache(path)
        if data is None:
            data = cls._download(user_agent, timeout)
            cls._write_cache(path, data)
        return cls(cls._parse(data))

    def get(self, ticker: str) -> Company | None:
        """Return the company for an exact ticker symbol, or ``None``."""
        return self._by_ticker.get(ticker.upper())

    def resolve(self, query: str, *, score_cutoff: float = 88.0) -> Company | None:
        """Resolve a query to a single company.

        Resolution is attempted in order: exact ticker, exact core name, then a
        length-aware fuzzy match against core names. The fuzzy step uses
        ``token_sort_ratio`` (rather than a partial scorer) so that a short,
        generic word such as "oil" does not match a longer company name that
        merely contains it. Callers should treat a ``None`` result as a term to
        match literally.

        Args:
            query: A ticker symbol or company name.
            score_cutoff: Minimum fuzzy score (0-100) for a name match.

        Returns:
            The best-matching company, or ``None`` if nothing matched
            confidently.
        """
        query = query.strip()
        if not query:
            return None
        exact = self._by_ticker.get(query.upper())
        if exact is not None:
            return exact
        core = _core_name(query)
        if core in self._by_core:
            return self._by_core[core]
        match = process.extractOne(
            core,
            self._cores,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=score_cutoff,
        )
        if match is None:
            return None
        return self._companies[match[2]]

    def mentions(self, text: str, ticker: str) -> bool:
        """Report whether text mentions the company for a ticker.

        A mention is either the ``$TICKER`` cashtag or the company's core name
        appearing as a whole word.

        Args:
            text: Text to search.
            ticker: Ticker symbol.

        Returns:
            ``True`` if the company is mentioned.
        """
        ticker = ticker.upper()
        pattern = self._mention_cache.get(ticker)
        if pattern is None:
            pattern = self._build_pattern(ticker)
            self._mention_cache[ticker] = pattern
        return pattern.search(text) is not None

    def _build_pattern(self, ticker: str) -> re.Pattern[str]:
        """Build the mention regex for a ticker (cashtag plus optional name)."""
        alternatives = [rf"(?<![A-Za-z0-9])\${re.escape(ticker)}\b"]
        company = self._by_ticker.get(ticker)
        if company is not None and len(company.core) >= 3:
            alternatives.append(rf"\b{re.escape(company.core)}\b")
        return re.compile("|".join(alternatives), re.IGNORECASE)

    @staticmethod
    def _read_cache(path: Path) -> dict | None:
        """Return cached data if present and fresh, otherwise ``None``."""
        try:
            if time.time() - path.stat().st_mtime > _CACHE_TTL_SECONDS:
                return None
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_cache(path: Path, data: dict) -> None:
        """Write data to the cache, ignoring filesystem errors."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
        except OSError:
            pass

    @staticmethod
    def _download(user_agent: str, timeout: float) -> dict:
        """Download the company list from the SEC."""
        resp = httpx.get(
            SEC_TICKERS_URL,
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse(data: dict) -> list[Company]:
        """Convert the SEC JSON payload into ``Company`` records."""
        companies = []
        for row in data.values():
            try:
                ticker = str(row["ticker"]).upper().strip()
                name = str(row["title"]).strip()
            except (KeyError, TypeError):
                continue
            core = _core_name(name)
            if ticker and core:
                companies.append(Company(ticker, name, core))
        return companies
