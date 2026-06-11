"""Deduplication of headlines by title.

Two layers are combined. An exact LRU set catches feeds that re-list the same
item on every poll. A fuzzy comparison against a sliding window of recent titles
catches near-duplicates, such as the same story reworded across different wires.
"""

from __future__ import annotations

from collections import OrderedDict, deque

from rapidfuzz import fuzz, process


class Deduper:
    """Tracks seen headline titles and reports whether a title is new."""

    def __init__(
        self,
        capacity: int = 5000,
        fuzzy_window: int = 400,
        threshold: float = 88.0,
    ) -> None:
        """Initialize the deduper.

        Args:
            capacity: Maximum number of exact titles to remember.
            fuzzy_window: Number of recent titles compared for fuzzy matches.
            threshold: Similarity score (0-100) at or above which two titles are
                considered duplicates. Set to 0 to disable fuzzy matching.
        """
        self.capacity = capacity
        self.threshold = threshold
        self._exact: OrderedDict[str, None] = OrderedDict()
        self._recent: deque[str] = deque(maxlen=fuzzy_window)

    def is_new(self, normalized_title: str) -> bool:
        """Report whether a title has not been seen before.

        Re-seeing an exact title refreshes its recency so that frequently
        re-listed items are not evicted while still live in a feed.

        Args:
            normalized_title: The headline's normalized title.

        Returns:
            ``True`` the first time a title or a close variant is seen, and
            ``False`` for subsequent exact or fuzzy duplicates.
        """
        if normalized_title in self._exact:
            self._exact.move_to_end(normalized_title)
            return False
        if self.threshold > 0 and self._recent:
            match = process.extractOne(
                normalized_title,
                self._recent,
                scorer=fuzz.token_set_ratio,
                score_cutoff=self.threshold,
            )
            if match is not None:
                self._remember(normalized_title)
                self._recent.append(normalized_title)
                return False
        self._remember(normalized_title)
        self._recent.append(normalized_title)
        return True

    def _remember(self, title: str) -> None:
        """Record a title in the exact LRU set, evicting the oldest if full."""
        self._exact[title] = None
        if len(self._exact) > self.capacity:
            self._exact.popitem(last=False)
