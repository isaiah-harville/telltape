"""Settings dialog for the contact email, theme, max age, and key bindings."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static

from .contact import _EMAIL_RE


class SettingsScreen(ModalScreen[dict | None]):
    """Modal for editing settings.

    Dismisses with a dictionary of the new values, or ``None`` if cancelled.
    The theme is applied live as a preview and reverted if the dialog is
    cancelled. The contact email is saved on its own, via its dedicated button,
    rather than as part of the main Save.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]
    # The contact email is consequential, so it is not auto-focused or
    # auto-selected; the user must click into it deliberately.
    AUTO_FOCUS = None

    class SaveEmail(Message):
        """Posted when the user saves the contact email on its own button."""

        def __init__(self, email: str) -> None:
            super().__init__()
            self.email = email

    def __init__(
        self,
        *,
        contact_email: str,
        max_age: float | None,
        theme: str,
        vim_keys: bool,
        poll_scale: float,
        source_names: list[str],
        key_bindings: dict[str, str],
    ) -> None:
        super().__init__()
        self._contact_email = contact_email
        self._max_age = max_age
        self._theme = theme
        self._original_theme = theme
        self._vim_keys = vim_keys
        self._poll_scale = poll_scale
        self._source_names = source_names
        self._key_bindings = key_bindings

    def compose(self) -> ComposeResult:
        themes = sorted(self.app.available_themes)
        with Vertical(id="settings-box"):
            yield Label("Settings", id="settings-title")
            yield Label(
                "Contact email — sent to data providers; required for SEC feeds"
            )
            with Horizontal(classes="email-row"):
                yield Input(
                    value=self._contact_email,
                    id="contact",
                    placeholder="you@example.com",
                    select_on_focus=False,
                )
                yield Button("Save email", id="save_email")
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
                "Poll speed — interval multiplier (1.0 = default, lower = faster; "
                "SEC filings unaffected)"
            )
            yield Input(value=str(self._poll_scale), id="poll_scale", placeholder="1.0")
            yield Checkbox(
                "Vim keys — j/k/g/G and ctrl-d/ctrl-u to navigate",
                value=self._vim_keys,
                id="vim_keys",
            )
            yield Label(
                "Key bindings — assign a source to each number key (blank = unbound)"
            )
            options = [("(unbound)", "")] + [(n, n) for n in self._source_names]
            # Nine Selects would make the dialog very tall, so they live in their
            # own bounded, scrollable area and the rest of the form stays in view.
            with VerticalScroll(id="kb-scroll"):
                for i in range(1, 10):
                    bound = self._key_bindings.get(str(i), "")
                    with Horizontal(classes="kb-row"):
                        yield Static(f"{i}", classes="kb-key")
                        yield Select(
                            options,
                            value=bound or "",
                            id=f"kb_{i}",
                            allow_blank=False,
                        )
            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def _fmt_age(self) -> str:
        return "" if self._max_age is None else str(int(self._max_age))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "theme":
            return
        if event.value is not Select.BLANK:
            self.app.theme = str(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_cancel()
            return
        if event.button.id == "save_email":
            self._save_email()
            return

        raw_age = self.query_one("#max_age", Input).value.strip()
        try:
            max_age = float(raw_age) if raw_age else None
        except ValueError:
            max_age = None
        raw_scale = self.query_one("#poll_scale", Input).value.strip()
        try:
            poll_scale = float(raw_scale) if raw_scale else 1.0
        except ValueError:
            poll_scale = 1.0
        poll_scale = min(10.0, max(0.25, poll_scale))
        key_bindings: dict[str, str] = {}
        for i in range(1, 10):
            val = self.query_one(f"#kb_{i}", Select).value
            if val:
                key_bindings[str(i)] = str(val)
        self.dismiss(
            {
                "max_age": max_age,
                "theme": str(self.query_one("#theme", Select).value),
                "vim_keys": self.query_one("#vim_keys", Checkbox).value,
                "poll_scale": poll_scale,
                "key_bindings": key_bindings,
            }
        )

    def _save_email(self) -> None:
        """Validate and persist the contact email without closing the dialog."""
        email = self.query_one("#contact", Input).value.strip()
        if not _EMAIL_RE.match(email):
            self.notify("Please enter a valid email address.", severity="warning")
            return
        self.post_message(self.SaveEmail(email))
        self.notify("Contact email saved")

    def action_cancel(self) -> None:
        # Revert the live theme preview before closing.
        self.app.theme = self._original_theme
        self.dismiss(None)
