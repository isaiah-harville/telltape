"""The main Textual application.

Shows a live scrolling tape of headlines with a toggleable source list. On first
run it requires a contact email and stores it. Sources are toggled by clicking or
pressing number keys. Settings configure the contact email, theme, and key
bindings; the Alerts dialog holds the watchlist, highlight keyword, and alerts.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

from textual import events
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, SelectionList
from textual.widgets.selection_list import Selection

from ..companies import CompanyTable
from ..config import load_config, save_config
from ..engine import NewsEngine
from ..feeds import load_feeds
from ..models import FeedSource, Headline
from ..render import format_headline
from ..watchlist import Watchlist
from .alerts import AlertsScreen
from .catalog import SourceCatalogScreen
from .contact import ContactScreen
from .quit import QuitScreen
from .settings import SettingsScreen

# Most lines kept in view; the buffer holds a little more so age-sorting and
# max-age filtering have headroom.
_TAPE_LINES = 500
_BUFFER_LINES = 2000


class TapeLog(RichLog):
    """A RichLog whose lines open their source URL on double-click."""

    def on_click(self, event: events.Click) -> None:
        # ``chain`` is the number of rapid successive clicks; 2 is a double-click.
        if event.chain != 2:
            return
        url = event.style.meta.get("url")
        if url:
            self.app.open_url(url)
            event.stop()


class TelltapeApp(App[None]):
    """The telltape terminal interface."""

    CSS = """
    #body { height: 1fr; }
    #sources { width: 48; border: round $accent; padding: 0 1; }
    #tape { border: round $accent; padding: 0 1; }

    SettingsScreen, ContactScreen, QuitScreen, AlertsScreen { align: center middle; }
    #settings-box, #contact-box, #quit-box, #alerts-box {
        width: 72; max-width: 95%; height: auto; max-height: 95%;
        overflow-y: auto; padding: 1 2;
        border: thick $accent; background: $surface;
    }
    #quit-box { width: 48; }
    #alerts-box { width: 80; }
    #settings-title, #contact-title, #quit-title, #alerts-title {
        text-style: bold; width: 1fr; text-align: center;
    }
    #settings-box Label, #contact-box Label, #quit-box Label, #alerts-box Label {
        margin-top: 1; color: $text-muted; width: 1fr;
    }
    .email-row { height: auto; }
    .email-row Input { width: 1fr; }
    .email-row Button { margin-left: 1; width: auto; min-width: 14; }
    #contact-error { color: $error; }
    #settings-buttons, #contact-buttons, #quit-buttons, #alerts-buttons {
        height: auto; margin-top: 1; align-horizontal: right;
    }
    #settings-buttons Button, #contact-buttons Button, #quit-buttons Button,
    #alerts-buttons Button {
        margin-left: 2;
    }
    #kb-scroll { height: auto; max-height: 12; border: round $panel; padding: 0 1; }
    .kb-row { height: 3; margin-top: 0; }
    .kb-key { width: 3; content-align: right middle; padding-right: 1; color: $text-muted; }
    .kb-row Select { width: 1fr; }

    SourceCatalogScreen { align: center middle; }
    #catalog-box {
        width: 90; max-width: 95%; height: 90%; max-height: 95%;
        padding: 1 2; border: thick $accent; background: $surface;
    }
    #catalog-title { text-style: bold; width: 1fr; text-align: center; }
    #catalog-hint { color: $text-muted; margin-bottom: 1; }
    #catalog-list { height: 1fr; }
    .catalog-group { text-style: bold; color: $accent; margin-top: 1; }
    .catalog-section { height: auto; border: none; padding: 0; }
    #catalog-buttons { height: auto; margin-top: 1; align-horizontal: right; }
    #catalog-buttons Button { margin-left: 2; }
    """
    TITLE = "telltape"
    SUB_TITLE = "live tape"
    BINDINGS = [
        ("s", "settings", "Settings"),
        ("b", "browse_sources", "Catalog"),
        ("a", "alerts", "Alerts"),
        ("t", "toggle_pause", "Pause"),
        ("c", "clear_tape", "Clear"),
        ("A", "all_sources", "All on"),
        ("X", "no_sources", "All off"),
        ("q", "confirm_quit", "Quit"),
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
        # Watchlist, keyword, and alerts are restored from the saved config so
        # they persist across restarts; the company table is attached later.
        self.settings: dict = {"max_age": None, "keyword": self.config.keyword}
        self.watchlist = Watchlist(self.config.watchlist)
        self.alerts = Watchlist(self.config.alerts)
        self.engine = NewsEngine(
            on_headline=self._on_headline,
            user_agent=self.config.user_agent,
            dedup_threshold=self.config.fuzzy_threshold,
            poll_scale=self.config.poll_scale,
        )
        self._tape: RichLog | None = None
        # Recent headlines kept so the tape can be repainted sorted by age.
        self._buffer: deque[tuple[Headline, bool]] = deque(maxlen=_BUFFER_LINES)
        # Guards against persisting the source selection during initial mount.
        self._sources_ready = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield SelectionList(*self._initial_selections(), id="sources")
            yield TapeLog(
                id="tape", wrap=True, markup=False, highlight=False, max_lines=2000
            )
        yield Footer()

    def _effective_key_map(self) -> dict[str, str]:
        """Return a {source_name: key} map using config bindings or positional fallback."""
        if self.config.key_bindings:
            return {name: k for k, name in self.config.key_bindings.items()}
        return {src.name: str(i + 1) for i, src in enumerate(self.sources) if i < 9}

    def _enabled_source_names(self) -> set[str]:
        """Return which sources should start enabled.

        Uses the user's last saved selection when one exists, otherwise each
        source's ``default_on``.
        """
        if self.config.enabled_sources is not None:
            return {n for n in self.config.enabled_sources if n in self._by_name}
        return {s.name for s in self.sources if s.default_on}

    def _initial_selections(self) -> list[Selection]:
        """Build the source selections as fixed-width columns.

        Each row is ``key  name  category  group`` with the columns padded to a
        constant width so the list reads as a table rather than ragged text.
        """
        key_map = self._effective_key_map()
        enabled = self._enabled_source_names()
        selections = []
        for src in self.sources:
            key = key_map.get(src.name) or ""
            label = f"{key:<2}{src.name:<18.18} {src.category:<7.7} {src.group:<11.11}"
            selections.append(Selection(label, src.name, src.name in enabled))
        return selections

    def on_mount(self) -> None:
        self.theme = self.config.theme
        self.query_one(
            "#sources", SelectionList
        ).border_title = "Sources  (click / 1-9)"
        self._tape = self.query_one("#tape", RichLog)
        self._tape.border_title = "Live tape"
        # Repaint on a timer so ages tick up and ordering stays correct even
        # between arrivals.
        self.set_interval(1.0, self._repaint)
        for message in self._load_errors:
            self.notify(message, title="Config", severity="warning", timeout=10)
        enabled = self._enabled_source_names()
        initial = [s for s in self.sources if s.name in enabled]
        self.run_worker(self.engine.run(initial=initial), name="engine")
        self._sources_ready = True
        if self.config.contact_email:
            self.run_worker(self._load_company_table(), name="companies")
        else:
            self.push_screen(ContactScreen(), self._on_contact_provided)

    def _on_contact_provided(self, email: str | None) -> None:
        if email:
            self.apply_contact_email(email)

    def apply_contact_email(self, email: str) -> None:
        """Persist a new contact email and refresh anything that depends on it."""
        if email == self.config.contact_email:
            return
        self.config.contact_email = email
        save_config(self.config)
        self.engine.set_user_agent(self.config.user_agent)
        self.run_worker(self._load_company_table(), name="companies")

    def on_settings_screen_save_email(self, message: SettingsScreen.SaveEmail) -> None:
        self.apply_contact_email(message.email)

    async def _load_company_table(self) -> None:
        """Load the SEC company table in the background and update the watchlist."""
        try:
            table = await asyncio.to_thread(
                CompanyTable.load, user_agent=self.config.user_agent
            )
        except asyncio.CancelledError:
            raise
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
        # Only the side panel drives the engine; the catalog's own lists, which
        # bubble the same event, are applied as a set when that dialog closes.
        if event.selection_list.id != "sources":
            return
        selected = set(event.selection_list.selected)
        active = self.engine.active_names
        for name in selected - active:
            self.engine.enable(self._by_name[name])
        for name in active - selected:
            self.engine.disable(name)
        if self._sources_ready:
            # Persist the selection (in source order) so it survives a restart.
            self.config.enabled_sources = [
                s.name for s in self.sources if s.name in selected
            ]
            save_config(self.config)

    def on_key(self, event) -> None:
        if len(event.key) == 1 and event.key in "123456789":
            bindings = self.config.key_bindings or {
                str(i + 1): src.name for i, src in enumerate(self.sources) if i < 9
            }
            source_name = bindings.get(event.key)
            if source_name and source_name in self._by_name:
                self.query_one("#sources", SelectionList).toggle(source_name)
                event.stop()
            return
        if self.config.vim_keys and self._handle_vim_key(event.key):
            event.stop()

    def _handle_vim_key(self, key: str) -> bool:
        """Route a vim navigation key to the focused pane.

        When the source list has focus, j/k/g/G move its cursor; otherwise the
        keys (plus ctrl-d/ctrl-u) scroll the tape. Returns whether the key was
        handled.
        """
        sources = self.query_one("#sources", SelectionList)
        if self.focused is sources:
            action = {
                "j": sources.action_cursor_down,
                "k": sources.action_cursor_up,
                "g": sources.action_first,
                "G": sources.action_last,
            }.get(key)
            if action is None:
                return False
            action()
            return True
        if self._tape is None:
            return False
        action = {
            "j": self._tape.scroll_down,
            "k": self._tape.scroll_up,
            "g": self._tape.scroll_home,
            "G": self._tape.scroll_end,
            "ctrl+d": self._tape.scroll_page_down,
            "ctrl+u": self._tape.scroll_page_up,
        }.get(key)
        if action is None:
            return False
        action()
        return True

    # --- headline sink ----------------------------------------------------

    def _on_headline(self, headline: Headline) -> None:
        """Buffer a new headline and refresh the tape.

        Items arrive out of published order across sources, so rather than
        appending we keep a buffer and repaint it sorted by age (see
        ``_repaint``). The alert bell/notification fires once here, on arrival.
        """
        if self.paused:
            return
        # An alert match is always shown, even if the watchlist would hide it.
        is_alert = self.alerts.active and self.alerts.matches(headline)
        if not (is_alert or self.watchlist.matches(headline)):
            return
        self._buffer.append((headline, is_alert))
        if is_alert:
            if self.config.alerts_sound:
                self.bell()
            self.notify(headline.title.strip(), title="Alert", severity="warning")
        self._repaint()

    def _repaint(self) -> None:
        """Render the buffered headlines sorted by published age.

        Called on each arrival and on a timer so ages stay current. The tape is
        cleared and rewritten oldest-first, so the freshest item sits at the
        bottom; items past ``max_age`` (and the oldest beyond the line cap) are
        dropped from view.
        """
        if self._tape is None or self.paused:
            return
        now = time.time()
        max_age = self.settings["max_age"]
        visible = [
            (h, alert)
            for (h, alert) in self._buffer
            if max_age is None or h.age is None or h.age <= max_age
        ]
        # Oldest first (newest at the bottom); undated items count as current.
        visible.sort(
            key=lambda ha: (ha[0].ts_published is None, ha[0].ts_published or now)
        )
        visible = visible[-_TAPE_LINES:]
        keyword = self.settings["keyword"]
        self._tape.clear()
        for headline, alert in visible:
            self._tape.write(format_headline(headline, keyword=keyword, alert=alert))

    # --- actions ----------------------------------------------------------

    def get_system_commands(self, screen: Screen):
        """Add the application's actions to the built-in command palette."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Settings", "Edit contact, theme, and key bindings", self.action_settings
        )
        yield SystemCommand(
            "Alerts", "Edit watchlist, highlight, alerts, and sound", self.action_alerts
        )
        yield SystemCommand(
            "Source catalog",
            "Browse and toggle every source by group",
            self.action_browse_sources,
        )
        yield SystemCommand(
            "Resume tape" if self.paused else "Pause tape",
            "Pause or resume the live tape",
            self.action_toggle_pause,
        )
        yield SystemCommand(
            "Clear tape", "Remove all headlines from the tape", self.action_clear_tape
        )
        yield SystemCommand(
            "Enable all sources", "Turn on every source", self.action_all_sources
        )
        yield SystemCommand(
            "Disable all sources", "Turn off every source", self.action_no_sources
        )

    def action_settings(self) -> None:
        self.push_screen(
            SettingsScreen(
                contact_email=self.config.contact_email,
                max_age=self.settings["max_age"],
                theme=self.config.theme,
                vim_keys=self.config.vim_keys,
                poll_scale=self.config.poll_scale,
                source_names=[s.name for s in self.sources],
                key_bindings=dict(self.config.key_bindings),
            ),
            self._apply_settings,
        )

    def action_alerts(self) -> None:
        self.push_screen(
            AlertsScreen(
                watchlist=self.watchlist.terms,
                keyword=self.settings["keyword"],
                alerts=self.alerts.terms,
                alerts_sound=self.config.alerts_sound,
            ),
            self._apply_alerts,
        )

    def _apply_alerts(self, result: dict | None) -> None:
        if result is None:
            return
        self.watchlist.set_terms(result["watchlist"])
        self.settings["keyword"] = result["keyword"]
        self.alerts.set_terms(result["alerts"])
        self.config.alerts_sound = result["alerts_sound"]
        # Persist the watchlist, keyword, and alert terms across restarts.
        self.config.watchlist = result["watchlist"]
        self.config.keyword = result["keyword"]
        self.config.alerts = result["alerts"]
        save_config(self.config)
        self.notify("Alerts updated")

    def action_browse_sources(self) -> None:
        sl = self.query_one("#sources", SelectionList)
        self.push_screen(
            SourceCatalogScreen(sources=self.sources, enabled=set(sl.selected)),
            self._apply_catalog,
        )

    def _apply_catalog(self, enabled: set[str] | None) -> None:
        """Sync the side panel to the catalog's enabled set, driving the engine."""
        if enabled is None:
            return
        sl = self.query_one("#sources", SelectionList)
        current = set(sl.selected)
        for name in self._by_name:
            if name in enabled and name not in current:
                sl.select(name)
            elif name not in enabled and name in current:
                sl.deselect(name)

    def _apply_settings(self, result: dict | None) -> None:
        if result is None:
            return
        self.settings["max_age"] = result["max_age"]
        self.config.vim_keys = result["vim_keys"]
        self.config.poll_scale = result["poll_scale"]
        # Takes effect on each source's next poll cycle.
        self.engine.poller.interval_scale = result["poll_scale"]

        if result["theme"] != self.config.theme:
            self.config.theme = result["theme"]
            self.theme = result["theme"]

        if result["key_bindings"] != self.config.key_bindings:
            self.config.key_bindings = result["key_bindings"]
            self._rebuild_source_list()

        save_config(self.config)
        self.notify("Settings updated")

    def _rebuild_source_list(self) -> None:
        """Refresh the source list labels to reflect updated key bindings."""
        sl = self.query_one("#sources", SelectionList)
        selected = set(sl.selected)
        sl.clear_options()
        for sel in self._initial_selections():
            sl.add_option(sel)
        for name in selected:
            if name in self._by_name:
                sl.select(name)

    def action_confirm_quit(self) -> None:
        def on_result(quit_app: bool | None) -> None:
            if quit_app:
                self.exit()

        self.push_screen(QuitScreen(), on_result)

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self.notify("Paused" if self.paused else "Resumed")
        if not self.paused:
            # Unfreeze: redraw immediately rather than waiting for the timer.
            self._repaint()

    def action_clear_tape(self) -> None:
        self._buffer.clear()
        if self._tape is not None:
            self._tape.clear()

    def action_all_sources(self) -> None:
        self.query_one("#sources", SelectionList).select_all()

    def action_no_sources(self) -> None:
        self.query_one("#sources", SelectionList).deselect_all()
