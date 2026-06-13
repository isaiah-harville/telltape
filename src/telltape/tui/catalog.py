"""Full-screen source catalog.

The side panel is built for quick toggling of a handful of sources by click or
number key. As the source list grows, this catalog gives a roomier view: every
source organized under its group with the URL and category visible, a search
box, and bulk enable/disable. It edits the same enabled set as the side panel,
which stays available for quick access.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from ..models import FeedSource


class SourceCatalogScreen(ModalScreen[set[str] | None]):
    """Modal browser for enabling and disabling sources by group.

    Dismisses with the set of enabled source names, or ``None`` if cancelled.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, *, sources: list[FeedSource], enabled: set[str]) -> None:
        """Initialize the catalog.

        Args:
            sources: All known sources, shown grouped in catalog order.
            enabled: Names of sources currently enabled.
        """
        super().__init__()
        self._sources = sources
        self._enabled = set(enabled)

    def compose(self) -> ComposeResult:
        with Vertical(id="catalog-box"):
            yield Label("Source catalog", id="catalog-title")
            yield Label(
                "Browse every source by group. Toggle with click or space; "
                "the side panel keeps your quick 1-9 access.",
                id="catalog-hint",
            )
            yield Input(placeholder="Search sources…", id="catalog-search")
            yield VerticalScroll(id="catalog-list")
            with Horizontal(id="catalog-buttons"):
                yield Button("Enable all", id="cat-all")
                yield Button("Disable all", id="cat-none")
                yield Button("Save", variant="primary", id="cat-save")
                yield Button("Cancel", id="cat-cancel")

    def on_mount(self) -> None:
        self._render("")

    # --- grouping ---------------------------------------------------------

    def _ordered_groups(self) -> list[str]:
        """Return group labels in first-seen order, with ungrouped last."""
        seen: list[str] = []
        for src in self._sources:
            label = src.group or "Other"
            if label not in seen:
                seen.append(label)
        return seen

    def _render(self, query: str) -> None:
        """Rebuild the grouped lists, showing only sources matching ``query``.

        Selections made since the last render are harvested first so toggles
        survive searching.
        """
        self._harvest()
        needle = query.strip().lower()
        container = self.query_one("#catalog-list", VerticalScroll)
        container.remove_children()
        for group in self._ordered_groups():
            members = [
                s
                for s in self._sources
                if (s.group or "Other") == group and self._matches(s, needle)
            ]
            if not members:
                continue
            container.mount(Label(group, classes="catalog-group"))
            options = [
                Selection(f"{s.name}  ·  {s.category}", s.name, s.name in self._enabled)
                for s in members
            ]
            container.mount(SelectionList(*options, classes="catalog-section"))

    @staticmethod
    def _matches(source: FeedSource, needle: str) -> bool:
        if not needle:
            return True
        return (
            needle in source.name.lower()
            or needle in source.group.lower()
            or needle in source.category.lower()
        )

    def _harvest(self) -> None:
        """Fold the currently visible selections back into the enabled set."""
        for sl in self.query(SelectionList):
            visible = {sl.get_option_at_index(i).value for i in range(sl.option_count)}
            self._enabled -= visible
            self._enabled |= set(sl.selected)

    # --- events -----------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "catalog-search":
            self._render(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cat-cancel":
            self.dismiss(None)
        elif event.button.id == "cat-all":
            for sl in self.query(SelectionList):
                sl.select_all()
        elif event.button.id == "cat-none":
            for sl in self.query(SelectionList):
                sl.deselect_all()
        elif event.button.id == "cat-save":
            self._harvest()
            self.dismiss(self._enabled)

    def action_cancel(self) -> None:
        self.dismiss(None)
