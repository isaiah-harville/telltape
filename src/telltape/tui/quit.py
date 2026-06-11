"""Confirmation dialog shown before leaving the application.

Quitting is cheap to trigger by a stray ``q`` keypress, so the tape is only torn
down once the user confirms. The screen dismisses with ``True`` to quit and
``False`` (or by cancelling) to stay.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitScreen(ModalScreen[bool]):
    """Modal asking the user to confirm quitting."""

    BINDINGS = [("escape", "cancel", "Stay")]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-box"):
            yield Label("Quit telltape?", id="quit-title")
            yield Label("The live tape will stop.")
            with Horizontal(id="quit-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Quit", variant="error", id="quit")

    def on_mount(self) -> None:
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "quit")

    def action_cancel(self) -> None:
        self.dismiss(False)
