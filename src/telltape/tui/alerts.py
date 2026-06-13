"""Dedicated alerts dialog.

Everything that shapes what a trader watches for lives here, separate from the
general settings: the watchlist the tape is filtered to, the highlighted
keyword, the alert terms that break through with a bell and a notification, and
the alert sound. All of it persists across restarts.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label


def _split(value: str) -> list[str]:
    """Split a comma-separated input into trimmed, non-empty terms."""
    return [t.strip() for t in value.split(",") if t.strip()]


class AlertsScreen(ModalScreen[dict | None]):
    """Modal for the watchlist, highlight keyword, alert terms, and alert sound.

    Dismisses with a dictionary of the new values, or ``None`` if cancelled.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        *,
        watchlist: list[str],
        keyword: str,
        alerts: list[str],
        alerts_sound: bool,
    ) -> None:
        super().__init__()
        self._watchlist = watchlist
        self._keyword = keyword
        self._alerts = alerts
        self._alerts_sound = alerts_sound

    def compose(self) -> ComposeResult:
        with Vertical(id="alerts-box"):
            yield Label("Alerts & watchlist", id="alerts-title")
            yield Label(
                "Watchlist — tickers or company names, comma separated. "
                "Blank shows everything."
            )
            yield Input(
                value=", ".join(self._watchlist),
                id="watchlist",
                placeholder="AAPL, Tesla, oil",
            )
            yield Label("Highlight keyword — emphasized wherever it appears")
            yield Input(value=self._keyword, id="keyword", placeholder="e.g. war")
            yield Label(
                "Alerts — notify on these tickers or keywords, comma separated. "
                "Matches are always shown, even when the watchlist would hide them."
            )
            yield Input(
                value=", ".join(self._alerts),
                id="alerts",
                placeholder="AAPL, recall, bankruptcy",
            )
            yield Checkbox(
                "Play sound on alerts", value=self._alerts_sound, id="alerts_sound"
            )
            with Horizontal(id="alerts-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#watchlist", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self.dismiss(
            {
                "watchlist": _split(self.query_one("#watchlist", Input).value),
                "keyword": self.query_one("#keyword", Input).value.strip(),
                "alerts": _split(self.query_one("#alerts", Input).value),
                "alerts_sound": self.query_one("#alerts_sound", Checkbox).value,
            }
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
