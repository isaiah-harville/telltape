"""First-run dialog requiring a contact email.

Data providers expect a contact in the request User-Agent, so the application
cannot operate fully without one. This screen blocks until a valid email is
entered; the caller is responsible for persisting it so the prompt is shown only
once.
"""

from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactScreen(ModalScreen[str]):
    """Modal that collects and validates a contact email.

    Dismisses with the validated email. It has no cancel path, so it must be
    pushed in a context where blocking the user until they provide one is
    acceptable.
    """

    def __init__(self, initial: str = "") -> None:
        """Initialize the dialog.

        Args:
            initial: Pre-filled email value.
        """
        super().__init__()
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="contact-box"):
            yield Label("Welcome to telltape", id="contact-title")
            yield Label(
                "Enter a contact email. It is sent to data providers (such as "
                "the SEC) to identify this client and is stored only on this "
                "machine."
            )
            yield Input(value=self._initial, id="email", placeholder="you@example.com")
            yield Label("", id="contact-error")
            with Horizontal(id="contact-buttons"):
                yield Button("Continue", variant="primary", id="continue")

    def on_mount(self) -> None:
        self.query_one("#email", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._submit()

    def _submit(self) -> None:
        email = self.query_one("#email", Input).value.strip()
        if not _EMAIL_RE.match(email):
            self.query_one("#contact-error", Label).update(
                "Please enter a valid email address."
            )
            return
        self.dismiss(email)
