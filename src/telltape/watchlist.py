"""Filtering of headlines against a user watchlist.

A watchlist is a list of free-text terms. Each term is resolved against the
company table: terms that resolve to a company are matched by ticker or company
name, and terms that do not resolve are matched as plain text. With no terms,
every headline passes.
"""

from __future__ import annotations

from .companies import CompanyTable
from .models import Headline


class Watchlist:
    """Compiles watchlist terms and tests headlines against them."""

    def __init__(
        self,
        terms: list[str] | None = None,
        table: CompanyTable | None = None,
    ) -> None:
        """Initialize the watchlist.

        Args:
            terms: Initial watchlist terms.
            table: Company table used to resolve terms to tickers.
        """
        self._terms: list[str] = list(terms or [])
        self._table = table
        # Compiled entries as (kind, value), where kind is "ticker" or "text".
        self._compiled: list[tuple[str, str]] = []
        self._compile()

    @property
    def terms(self) -> list[str]:
        """Return the current watchlist terms."""
        return list(self._terms)

    @property
    def active(self) -> bool:
        """Return whether any terms are set."""
        return bool(self._compiled)

    def set_terms(self, terms: list[str]) -> None:
        """Replace the watchlist terms and recompile."""
        self._terms = list(terms)
        self._compile()

    def set_table(self, table: CompanyTable | None) -> None:
        """Set the company table and recompile, upgrading text terms to tickers."""
        self._table = table
        self._compile()

    def matches(self, headline: Headline) -> bool:
        """Report whether a headline matches the watchlist.

        Args:
            headline: Headline to test.

        Returns:
            ``True`` if the watchlist is empty or the headline matches any term.
        """
        if not self._compiled:
            return True
        held = {t.upper() for t in headline.tickers}
        for kind, value in self._compiled:
            if kind == "ticker":
                if value in held:
                    return True
                if self._table is not None and self._table.mentions(headline.title, value):
                    return True
            elif value in headline.title.lower():
                return True
        return False

    def _compile(self) -> None:
        """Resolve each term to a ticker or fall back to a text match."""
        compiled: list[tuple[str, str]] = []
        for term in self._terms:
            company = self._table.resolve(term) if self._table is not None else None
            if company is not None:
                compiled.append(("ticker", company.ticker))
            else:
                compiled.append(("text", term.lower()))
        self._compiled = compiled
