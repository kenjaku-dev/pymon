"""Textual application for pymon."""

from __future__ import annotations

import asyncio
import logging

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, Static, TabbedContent, TabPane

from pymon.collectors import SystemCollector
from pymon.collectors.models import SystemSnapshot
from pymon.config import Config
from pymon.ui.panels import (
    CpuPanel,
    DiskPanel,
    GpuPanel,
    HeaderBar,
    MemoryPanel,
    NetworkPanel,
    ProcessTable,
    SensorsPanel,
    SystemInfoPanel,
)

logger = logging.getLogger("pymon.app")

CSS = """
Screen {
    layout: vertical;
}
#header { height: 3; }
TabbedContent { height: 1fr; }
#overview {
    layout: grid;
    grid-size: 3 3;
    grid-columns: 1fr 1fr 1fr;
    grid-rows: auto auto auto;
}
#cpu { column-span: 3; }
#mem { }
#disk { }
#net { }
#gpu { column-span: 1; }
#sensors { column-span: 2; }
#processes-tab {
    layout: vertical;
}
#sysinfo-tab {
    layout: vertical;
}
#sysinfo { height: 1fr; }
#processes { height: 1fr; }
#filterbar { height: 3; display: none; }
#filterbar.visible { display: block; }
"""


class ConfirmScreen(ModalScreen[bool]):
    """Simple yes/no confirmation modal."""

    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    #confirm-box { width: 50; height: auto; border: round $primary; padding: 1 2;
                  background: $surface; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Static(self._message, id="confirm-msg")
        yield Static("Press [b]y[/b] to confirm, [b]n[/b]/Esc to cancel.", id="confirm-hint")

    def on_key(self, event: events.Key) -> None:
        if event.key in ("y", "Y"):
            self.dismiss(True)
        elif event.key in ("n", "N", "escape"):
            self.dismiss(False)


class HelpScreen(ModalScreen[None]):
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    #help-box { width: 60; height: auto; border: round $primary; padding: 1 2;
                background: $surface; }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        text = Text()
        text.append("pymon keybindings\n", style="bold")
        bindings = [
            ("q", "quit"),
            ("p", "pause/resume refresh"),
            ("r", "force refresh"),
            ("k", "kill selected process (SIGTERM)"),
            ("K", "kill selected process (SIGKILL)"),
            ("/", "filter processes"),
            ("s", "cycle sort column"),
            ("a", "toggle sort direction"),
            ("+ / -", "adjust refresh interval"),
            ("1 / 2 / 3", "switch tabs (overview / processes / system info)"),
            ("Tab", "next tab"),
            ("h", "this help"),
            ("Esc", "close modal / clear filter"),
        ]
        for k, v in bindings:
            text.append(f"  {k:<8}", style="bold cyan")
            text.append(f"{v}\n")
        yield Static(text, id="help-box")

    async def action_dismiss(self, result=None) -> None:
        self.dismiss(None)


class PymonApp(App):
    CSS = CSS
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause"),
        Binding("r", "force_refresh", "Refresh"),
        Binding("k", "kill_term", "Kill"),
        Binding("K", "kill_kill", "Kill9"),
        Binding("slash", "toggle_filter", "Filter"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("a", "toggle_sort_dir", "Asc/Desc"),
        Binding("plus", "faster", "Faster"),
        Binding("minus", "slower", "Slower"),
        Binding("h", "help", "Help"),
        Binding("1", "show_overview", "Overview"),
        Binding("2", "show_processes", "Processes"),
        Binding("3", "show_sysinfo", "System Info"),
        Binding("tab", "next_tab", "Next tab", show=False),
        Binding("escape", "escape", "Esc"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.collector = SystemCollector()
        self.snapshot: SystemSnapshot | None = None
        self._paused = False
        self._collecting = False
        self._filter_text = ""
        self._filter_visible = False
        self._sort_cols = ["cpu", "mem", "pid", "name"]
        self._sort_idx = (
            self._sort_cols.index(config.process_sort)
            if config.process_sort in self._sort_cols
            else 0
        )
        self._sort_desc = config.process_sort_desc
        # apply config sort
        self.config.process_sort = self._sort_cols[self._sort_idx]
        self.config.process_sort_desc = self._sort_desc

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        with TabbedContent(initial="overview"):
            with TabPane("Overview", id="overview"):
                yield CpuPanel(id="cpu")
                yield MemoryPanel(id="mem")
                yield DiskPanel(id="disk")
                yield NetworkPanel(id="net")
                yield GpuPanel(id="gpu")
                yield SensorsPanel(id="sensors")
            with TabPane("Processes", id="processes-tab"):
                yield ProcessTable(id="processes")
                yield Input(placeholder="filter processes...", id="filterbar")
            with TabPane("System Info", id="sysinfo-tab"):
                yield SystemInfoPanel(id="sysinfo")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#processes", ProcessTable)
        table.setup_columns(self.config.process_columns)
        self.set_interval(self.config.clamped_interval(), self._tick)
        # initial collect
        self.run_worker(self._collect_and_apply, thread=True)

    async def _tick(self) -> None:
        if self._paused or self._collecting:
            return
        self._collecting = True
        try:
            snap = await asyncio.to_thread(self._collect)
            self._apply(snap)
        except Exception as e:  # pragma: no cover
            logger.exception("collect failed: %s", e)
        finally:
            self._collecting = False

    def _collect(self) -> SystemSnapshot:
        return self.collector.collect(
            process_row_cap=self.config.process_row_cap,
            process_sort=self.config.process_sort,
            process_sort_desc=self.config.process_sort_desc,
            show_all_interfaces=self.config.show_all_interfaces,
            show_all_partitions=self.config.show_all_partitions,
        )

    def _collect_and_apply(self) -> None:
        if self._collecting:
            return
        self._collecting = True
        try:
            snap = self._collect()
            self.call_from_thread(self._apply, snap)
        finally:
            self._collecting = False

    def _apply(self, snap: SystemSnapshot) -> None:
        self.snapshot = snap
        # update config sort state already in config
        self.query_one("#header", HeaderBar).update_data(snap, self.config)
        self.query_one("#cpu", CpuPanel).update_data(snap, self.config)
        self.query_one("#mem", MemoryPanel).update_data(snap, self.config)
        self.query_one("#disk", DiskPanel).update_data(snap, self.config)
        self.query_one("#net", NetworkPanel).update_data(snap, self.config)
        self.query_one("#gpu", GpuPanel).update_data(snap, self.config)
        self.query_one("#sensors", SensorsPanel).update_data(snap, self.config)
        self.query_one("#sysinfo", SystemInfoPanel).update_data(snap, self.config)
        table = self.query_one("#processes", ProcessTable)
        table.update_data(snap, self.config, self._filter_text)

    # ---- actions ----

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self.notify("Paused" if self._paused else "Resumed")

    def action_force_refresh(self) -> None:
        if self._collecting:
            return
        self.run_worker(self._collect_and_apply, thread=True)

    def action_toggle_filter(self) -> None:
        self._filter_visible = not self._filter_visible
        fb = self.query_one("#filterbar", Input)
        if self._filter_visible:
            fb.add_class("visible")
            fb.display = True
            fb.focus()
        else:
            fb.display = False
            self._filter_text = ""
            fb.value = ""
            if self.snapshot is not None:
                self._apply(self.snapshot)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filterbar":
            self._filter_text = event.value
            if self.snapshot is not None:
                self.query_one("#processes", ProcessTable).update_data(
                    self.snapshot, self.config, self._filter_text
                )

    def action_cycle_sort(self) -> None:
        self._sort_idx = (self._sort_idx + 1) % len(self._sort_cols)
        self.config.process_sort = self._sort_cols[self._sort_idx]
        self.notify(f"Sort: {self.config.process_sort}")
        if self.snapshot is not None:
            # re-sort current processes in place
            self._resort_snapshot()
            self._apply(self.snapshot)

    def action_toggle_sort_dir(self) -> None:
        self._sort_desc = not self._sort_desc
        self.config.process_sort_desc = self._sort_desc
        self.notify("Desc" if self._sort_desc else "Asc")
        if self.snapshot is not None:
            self._resort_snapshot()
            self._apply(self.snapshot)

    def _resort_snapshot(self) -> None:
        if self.snapshot is None:
            return
        keymap = {
            "cpu": lambda x: x.cpu_percent,
            "mem": lambda x: x.memory_percent,
            "pid": lambda x: x.pid,
            "name": lambda x: x.name.lower(),
        }
        keyfn = keymap.get(self.config.process_sort, keymap["cpu"])
        self.snapshot.processes.sort(key=keyfn, reverse=self.config.process_sort_desc)
        self.snapshot.processes = self.snapshot.processes[: self.config.process_row_cap]

    def action_faster(self) -> None:
        self.config.refresh_interval = max(0.1, self.config.refresh_interval - 0.1)
        self._rearm_timer()
        self.notify(f"Interval {self.config.refresh_interval:.1f}s")

    def action_slower(self) -> None:
        self.config.refresh_interval = min(10.0, self.config.refresh_interval + 0.5)
        self._rearm_timer()
        self.notify(f"Interval {self.config.refresh_interval:.1f}s")

    def _rearm_timer(self) -> None:
        # textual timers can't easily change interval; recreate by removing old.
        # We stored no ref; find timers and stop, then set new.
        for t in list(self._timers):
            t.stop()
        self.set_interval(self.config.clamped_interval(), self._tick)

    def action_show_overview(self) -> None:
        self.query_one(TabbedContent).active = "overview"

    def action_show_processes(self) -> None:
        tc = self.query_one(TabbedContent)
        tc.active = "processes-tab"
        self.query_one("#processes", ProcessTable).focus()

    def action_show_sysinfo(self) -> None:
        self.query_one(TabbedContent).active = "sysinfo-tab"

    def action_next_tab(self) -> None:
        tc = self.query_one(TabbedContent)
        tabs = ["overview", "processes-tab", "sysinfo-tab"]
        try:
            idx = tabs.index(tc.active)
        except ValueError:
            idx = 0
        tc.active = tabs[(idx + 1) % len(tabs)]

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return not (action == "next_tab" and isinstance(self.focused, Input))

    def on_key(self, event: events.Key) -> None:
        if event.key == "tab" and not isinstance(self.focused, Input):
            event.prevent_default()
            event.stop()
            self.action_next_tab()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_escape(self) -> None:
        if self._filter_visible:
            self.action_toggle_filter()
        else:
            # pop modal if any
            if len(self.screen_stack) > 1:
                self.pop_screen()

    def action_kill_term(self) -> None:
        self._kill_selected(sig=15)

    def action_kill_kill(self) -> None:
        self._kill_selected(sig=9)

    def _selected_pid(self) -> int | None:
        table = self.query_one("#processes", ProcessTable)
        if table.row_count == 0:
            return None
        try:
            row = table.ordered_rows[table.cursor_row]
            value = getattr(row.key, "value", None)
            if value is None:
                return None
            return int(value)
        except (ValueError, TypeError, IndexError):
            return None

    def _kill_selected(self, sig: int) -> None:
        pid = self._selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning")
            return
        name = "SIGTERM" if sig == 15 else "SIGKILL"

        def do_kill(confirmed: bool | None) -> None:
            if not confirmed:
                return
            import os
            import signal as _signal

            try:
                os.kill(pid, _signal.SIGTERM if sig == 15 else _signal.SIGKILL)
                self.notify(f"Sent {name} to {pid}")
            except ProcessLookupError:
                self.notify(f"Process {pid} gone", severity="warning")
            except PermissionError:
                self.notify(f"Permission denied for {pid}", severity="error")

        self.push_screen(ConfirmScreen(f"Kill PID {pid} with {name}?"), do_kill)
