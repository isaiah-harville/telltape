"""The main Textual application.

Shows a live scrolling tape of headlines with a toggleable source list. On first
run it requires a contact email and stores it. Sources are toggled by clicking or
pressing number keys; settings configure the contact email, theme, and filters.
"""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, SelectionList
from textual.widgets.selection_list import Selection

from ..companies import CompanyTable
from ..config import Config, load_config, save_config
from ..engine import NewsEngine
from ..feeds import load_feeds
from ..models import FeedSource, Headline
from ..render import format_headline
from ..watchlist import Watchlist
from .contact import ContactScreen
from .settings import SettingsScreen


class TelltapeApp(App[None]):
    """The telltape terminal interface."""

    CSS = """
    #body { height: 1fr; }
    #sources { width: 38; border: round $accent; padding: 0 1; }
    #tape { border: round $accent; padding: 0 1; }

    SettingsScreen, ContactScreen { align: center middle; }
    #settings-box, #contact-box {
        width: 72; max-width: 95%; height: auto; max-height: 95%;
        overflow-y: auto; padding: 1 2;
        border: thick $accent; background: $surface;
    }
    #settings-title, #contact-title {
        text-style: bold; width: 1fr; text-align: center;
    }
    #settings-box Label, #contact-box Label { margin-top: 1; color: $text-muted; }
    #contact-error { color: $error; }
    #settings-buttons, #contact-buttons {
        height: auto; margin-top: 1; align-horizontal: right;
    }
    #settings-buttons Button, #contact-buttons Button { margin-left: 2; }
    """
    TITLE = "telltape"
    SUB_TITLE = "live tape"
    BINDINGS = [
        ("s", "settings", "Settings"),
        ("p", "toggle_pause", "Pause"),
        ("c", "clear_tape", "Clear"),
        ("a", "all_sources", "All on"),
        ("x", "no_sources", "All off"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, sources: list[FeedSource] | None = None) -> None:
        """Initialize the application.

        Args:
            sources: Sources to offer. Defaults to the built-in feed list.
        """
        super().__init__()
        if sources:
            self.sources: list[FeedSource] = list(sources)
            feeds_error = None
        else:
            self.sources, feeds_error = load_feeds()
        self._by_name = {s.name: s for s in self.sources}
        self.config, config_error = load_config()
        # Messages about unreadable config files, surfaced once the UI is up.
        self._load_errors = [e for e in (config_error, feeds_error) if e]
        self.paused = False
        self.settings: dict = {"max_age": None, "keyword": ""}
        self.watchlist = Watchlist()
        self.alerts = Watchlist()
        self.engine = NewsEngine(
            on_headline=self._on_headline,
            user_agent=self.config.user_agent,
            dedup_threshold=self.config.fuzzy_threshold,
        )
        self._tape: RichLog | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield SelectionList(*self._initial_selections(), id="sources")
            yield RichLog(id="tape", wrap=True, markup=False, highlight=False, max_lines=2000)
        yield Footer()

    def _initial_selections(self) -> list[Selection]:
        """Build the source selections, prefixing the first nine with a digit."""
        selections = []
        for i, src in enumerate(self.sources):
            prefix = f"{i + 1} " if i < 9 else "  "
            selections.append(Selection(f"{prefix}{src.name}", src.name, src.default_on))
        return selections

    def on_mount(self) -> None:
        self.theme = self.config.theme
        self.query_one("#sources", SelectionList).border_title = "Sources  (click / 1-9)"
        self._tape = self.query_one("#tape", RichLog)
        self._tape.border_title = "Live tape"
        for message in self._load_errors:
            self.notify(message, title="Config", severity="warning", timeout=10)
        initial = [s for s in self.sources if s.default_on]
        self.run_worker(self.engine.run(initial=initial), name="engine")
        if self.config.contact_email:
            self.run_worker(self._load_company_table(), name="companies")
        else:
            self.push_screen(ContactScreen(), self._on_contact_provided)

    def _on_contact_provided(self, email: str | None) -> None:
        if not email:
            return
        self.config.contact_email = email
        save_config(self.config)
        self.engine.set_user_agent(self.config.user_agent)
        self.run_worker(self._load_company_table(), name="companies")

    async def _load_company_table(self) -> None:
        """Load the SEC company table in the background and update the watchlist."""
        try:
            table = await asyncio.to_thread(
                CompanyTable.load, user_agent=self.config.user_agent
            )
        except Exception:
            self.notify(
                "Company list unavailable; check the contact email in Settings.",
                severity="warning",
            )
            return
        self.watchlist.set_table(table)
        self.alerts.set_table(table)

    # --- source toggling --------------------------------------------------

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        selected = set(event.selection_list.selected)
        active = self.engine.active_names
        for name in selected - active:
            self.engine.enable(self._by_name[name])
        for name in active - selected:
            self.engine.disable(name)

    def on_key(self, event) -> None:
        if len(event.key) == 1 and event.key in "123456789":
            index = int(event.key) - 1
            if index < len(self.sources):
                self.query_one("#sources", SelectionList).toggle(self.sources[index].name)
                event.stop()

    # --- headline sink ----------------------------------------------------

    def _on_headline(self, headline: Headline) -> None:
        if self.paused or self._tape is None:
            return
        if self.settings["max_age"] is not None:
            age = headline.age
            if age is not None and age > self.settings["max_age"]:
                return
        # An alert match is always shown, even if the watchlist would hide it.
        is_alert = self.alerts.active and self.alerts.matches(headline)
        if not (is_alert or self.watchlist.matches(headline)):
            return
        self._tape.write(
            format_headline(headline, keyword=self.settings["keyword"], alert=is_alert)
        )
        if is_alert:
            if self.config.alerts_sound:
                self.bell()
            self.notify(headline.title.strip(), title="Alert", severity="warning")

    # --- actions ----------------------------------------------------------

    def get_system_commands(self, screen: Screen):
        """Add the application's actions to the built-in command palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Settings", "Edit contact, theme, filters, and alerts", self.action_settings
        )
        yield SystemCommand(
            "Resume tape" if self.paused else "Pause tape",
            "Pause or resume the live tape",
            self.action_toggle_pause,
        )
        yield SystemCommand("Clear tape", "Remove all headlines from the tape", self.action_clear_tape)
        yield SystemCommand("Enable all sources", "Turn on every source", self.action_all_sources)
        yield SystemCommand("Disable all sources", "Turn off every source", self.action_no_sources)

    def action_settings(self) -> None:
        self.push_screen(
            SettingsScreen(
                contact_email=self.config.contact_email,
                max_age=self.settings["max_age"],
                filters=self.watchlist.terms,
                keyword=self.settings["keyword"],
                alerts=self.alerts.terms,
                alerts_sound=self.config.alerts_sound,
                theme=self.config.theme,
            ),
            self._apply_settings,
        )

    def _apply_settings(self, result: dict | None) -> None:
        if result is None:
            return
        self.settings = {"max_age": result["max_age"], "keyword": result["keyword"]}
        self.watchlist.set_terms(result["filters"])
        self.alerts.set_terms(result["alerts"])
        self.config.alerts_sound = result["alerts_sound"]

        if result["theme"] != self.config.theme:
            self.config.theme = result["theme"]
            self.theme = result["theme"]

        if result["contact_email"] != self.config.contact_email:
            self.config.contact_email = result["contact_email"]
            self.engine.set_user_agent(self.config.user_agent)
            self.run_worker(self._load_company_table(), name="companies")

        save_config(self.config)
        self.notify("Settings updated")

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self.notify("Paused" if self.paused else "Resumed")

    def action_clear_tape(self) -> None:
        if self._tape is not None:
            self._tape.clear()

    def action_all_sources(self) -> None:
        self.query_one("#sources", SelectionList).select_all()

    def action_no_sources(self) -> None:
        self.query_one("#sources", SelectionList).deselect_all()
