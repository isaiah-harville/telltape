"""Dedicated alerts dialog.

Alerts are kept separate from general settings because they are the one filter a
trader reaches for most often mid-session: the tickers or keywords that should
break through the watchlist with a bell and a notification. This modal edits the
alert terms and the alert sound.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label


class AlertsScreen(ModalScreen[dict | None]):
    """Modal for editing alert terms and the alert sound.

    Dismisses with a dictionary of the new values, or ``None`` if cancelled.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, *, alerts: list[str], alerts_sound: bool) -> None:
        super().__init__()
        self._alerts = alerts
        self._alerts_sound = alerts_sound

    def compose(self) -> ComposeResult:
        with Vertical(id="alerts-box"):
            yield Label("Alerts", id="alerts-title")
            yield Label(
                "Notify on these tickers or keywords, comma separated. Matches "
                "are always shown, even when the watchlist would hide them."
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
        self.query_one("#alerts", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        alerts = [
            t.strip()
            for t in self.query_one("#alerts", Input).value.split(",")
            if t.strip()
        ]
        self.dismiss(
            {
                "alerts": alerts,
                "alerts_sound": self.query_one("#alerts_sound", Checkbox).value,
            }
        )

    def action_cancel(self) -> None:
        self.dismiss(None)
