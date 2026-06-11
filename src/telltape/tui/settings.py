"""Settings dialog for the contact email, theme, and runtime filters."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select


class SettingsScreen(ModalScreen[dict | None]):
    """Modal for editing settings.

    Dismisses with a dictionary of the new values, or ``None`` if cancelled.
    The theme is applied live as a preview and reverted if the dialog is
    cancelled.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        *,
        contact_email: str,
        max_age: float | None,
        filters: list[str],
        keyword: str,
        alerts: list[str],
        alerts_sound: bool,
        theme: str,
    ) -> None:
        """Initialize the dialog.

        Args:
            contact_email: Current contact email.
            max_age: Current maximum age in seconds, or ``None``.
            filters: Current watchlist terms.
            keyword: Current highlight keyword.
            alerts: Current alert terms.
            alerts_sound: Whether the terminal bell rings on an alert.
            theme: Current theme name.
        """
        super().__init__()
        self._contact_email = contact_email
        self._max_age = max_age
        self._filters = filters
        self._keyword = keyword
        self._alerts = alerts
        self._alerts_sound = alerts_sound
        self._theme = theme
        self._original_theme = theme

    def compose(self) -> ComposeResult:
        themes = sorted(self.app.available_themes)
        with Vertical(id="settings-box"):
            yield Label("Settings", id="settings-title")
            yield Label(
                "Contact email — sent to data providers; required for SEC feeds"
            )
            yield Input(
                value=self._contact_email, id="contact", placeholder="you@example.com"
            )
            yield Label("Theme")
            yield Select(
                [(name, name) for name in themes],
                value=self._theme,
                id="theme",
                allow_blank=False,
            )
            yield Label("Max age — hide items older than N seconds (blank = no limit)")
            yield Input(value=self._fmt_age(), id="max_age", placeholder="e.g. 600")
            yield Label(
                "Watchlist — tickers or company names, comma separated (blank = all)"
            )
            yield Input(
                value=", ".join(self._filters),
                id="filters",
                placeholder="AAPL, Tesla, oil",
            )
            yield Label("Highlight keyword")
            yield Input(value=self._keyword, id="keyword", placeholder="e.g. war")
            yield Label("Alerts — notify on these tickers or keywords, comma separated")
            yield Input(
                value=", ".join(self._alerts),
                id="alerts",
                placeholder="AAPL, recall, bankruptcy",
            )
            yield Checkbox(
                "Play sound on alerts", value=self._alerts_sound, id="alerts_sound"
            )
            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def _fmt_age(self) -> str:
        return "" if self._max_age is None else str(int(self._max_age))

    def on_select_changed(self, event: Select.Changed) -> None:
        # Apply the chosen theme immediately as a live preview.
        if event.value is not Select.BLANK:
            self.app.theme = str(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_cancel()
            return

        raw_age = self.query_one("#max_age", Input).value.strip()
        try:
            max_age = float(raw_age) if raw_age else None
        except ValueError:
            max_age = None
        filters = [
            t.strip()
            for t in self.query_one("#filters", Input).value.split(",")
            if t.strip()
        ]
        alerts = [
            t.strip()
            for t in self.query_one("#alerts", Input).value.split(",")
            if t.strip()
        ]
        self.dismiss(
            {
                "contact_email": self.query_one("#contact", Input).value.strip(),
                "max_age": max_age,
                "filters": filters,
                "keyword": self.query_one("#keyword", Input).value.strip(),
                "alerts": alerts,
                "alerts_sound": self.query_one("#alerts_sound", Checkbox).value,
                "theme": str(self.query_one("#theme", Select).value),
            }
        )

    def action_cancel(self) -> None:
        # Revert the live theme preview before closing.
        self.app.theme = self._original_theme
        self.dismiss(None)
