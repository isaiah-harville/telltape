"""Detection of stock symbols written as cashtags.

Only explicit cashtags such as ``$AAPL`` are recognized here, which requires no
data and rarely produces false positives. Mapping arbitrary company names to
symbols is handled separately in :mod:`telltape.companies`.
"""

from __future__ import annotations

import re

# A dollar sign followed by one to five upper-case letters, optionally a class
# suffix such as .A or -B. The lookbehind prevents matching inside a token, so a
# price like "$50" or text such as "abc$X" is not treated as a cashtag.
_CASHTAG = re.compile(r"(?<![A-Za-z0-9])\$([A-Z]{1,5})(?:[.\-][A-Z])?\b")


def extract_tickers(*texts: str | None) -> tuple[str, ...]:
    """Extract unique cashtag symbols from one or more texts.

    Args:
        *texts: Strings to scan; ``None`` values are ignored.

    Returns:
        Unique upper-case symbols in the order first encountered.
    """
    seen: dict[str, None] = {}
    for text in texts:
        for symbol in _CASHTAG.findall(text or ""):
            seen.setdefault(symbol, None)
    return tuple(seen)
