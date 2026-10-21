"""TUI panels (Textual widgets)."""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import DataTable, Static

from pymon.collectors.models import SystemSnapshot
from pymon.collectors.system import get_system_info
from pymon.config import Config
from pymon.utils import bar, human_bytes, human_rate, sparkline


class HeaderBar(Static):
    DEFAULT_CSS = """
    HeaderBar { height: 3; padding: 0 1; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        text = Text()
        text.append(f"{snap.hostname}", style="bold cyan")
        text.append("  │  up ")
        text.append(_fmt_uptime(snap.uptime_seconds), style="green")
        if snap.cpu.load_avg:
            la = snap.cpu.load_avg
            text.append(f"  │  load {la[0]:.2f} {la[1]:.2f} {la[2]:.2f}")
        text.append(f"  │  {snap.timestamp and _fmt_time(snap.timestamp)}")
        if snap.errors:
            text.append(f"  │  errors: {len(snap.errors)}", style="red")
        self.update(text)


class CpuPanel(Static):
    DEFAULT_CSS = """
    CpuPanel { height: auto; padding: 1; border: round #556d59; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=40)

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        cpu = snap.cpu
        threshold = config.thresholds.cpu
        self._history.append(cpu.overall)
        text = Text()
        style = _usage_style(cpu.overall, threshold)
        text.append(f"CPU  {cpu.overall:5.1f}%  ", style=style)
        text.append(bar(cpu.overall, 18), style=style.split()[0])
        if cpu.overall >= threshold:
            text.append("  ⚠", style="red bold")
        text.append("\n")
        text.append(f"hist {sparkline(self._history, 24)}\n", style="dim")
        if cpu.freq_mhz:
            text.append(f"freq {cpu.freq_mhz:7.0f} MHz   ", style="dim")
        if cpu.temp_c is not None:
            text.append(f"temp {cpu.temp_c:4.1f}°C", style="dim")
        text.append("\n")
        # per-core
        cores = cpu.per_core
        for i, c in enumerate(cores):
            core_style = _usage_style(c, threshold).split()[0]
            text.append(f"c{i:<2} {c:5.1f}% ", style=core_style)
            text.append(bar(c, 10), style=core_style)
            if (i + 1) % 2 == 0:
                text.append("\n")
            else:
                text.append("  ")
        if len(cores) % 2:
            text.append("\n")
        self.update(text)


class MemoryPanel(Static):
    DEFAULT_CSS = """
    MemoryPanel { height: auto; padding: 1; border: round #6c6c4b; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=40)

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        m = snap.memory
        threshold = config.thresholds.memory
        self._history.append(m.percent)
        text = Text()
        style = _usage_style(m.percent, threshold)
        text.append(f"RAM  {m.percent:5.1f}%  ", style=style)
        text.append(bar(m.percent, 18), style=style.split()[0])
        if m.percent >= threshold:
            text.append("  ⚠", style="red bold")
        text.append("\n")
        text.append(f"hist {sparkline(self._history, 24)}\n", style="dim")
        text.append(
            f"{human_bytes(m.used)} / {human_bytes(m.total)}   avail {human_bytes(m.available)}\n",
            style="dim",
        )
        # swap
        swap_style = _usage_style(m.swap_percent, threshold).split()[0]
        text.append(f"SWAP {m.swap_percent:5.1f}%  ", style=swap_style)
        text.append(bar(m.swap_percent, 18), style=swap_style)
        text.append("\n")
        text.append(f"{human_bytes(m.swap_used)} / {human_bytes(m.swap_total)}", style="dim")
        self.update(text)


class DiskPanel(Static):
    DEFAULT_CSS = """
    DiskPanel { height: auto; padding: 1; border: round #8a6d3b; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        threshold = config.thresholds.disk
        text = Text()
        for d in sorted(snap.disks, key=lambda x: x.mountpoint):
            disk_style = _usage_style(d.percent, threshold)
            text.append(f"{d.mountpoint}", style="bold")
            text.append(f"  ({d.device}, {d.fstype})\n", style="dim")
            text.append(f"  {d.percent:5.1f}%  ", style=disk_style)
            text.append(bar(d.percent, 20), style=disk_style.split()[0])
            text.append(f"  {human_bytes(d.used)}/{human_bytes(d.total)}\n", style="dim")
        if snap.disk_io is not None:
            dio = snap.disk_io
            text.append(
                f"IO  R {human_rate(dio.read_rate)}  W {human_rate(dio.write_rate)}",
                style="dim",
            )
        if getattr(snap, "disk_io_per_device", None):
            for dev in sorted(snap.disk_io_per_device)[:5]:
                dio = snap.disk_io_per_device[dev]
                text.append(
                    f"  {dev}: R {human_rate(dio.read_rate)}  W {human_rate(dio.write_rate)}\n",
                    style="dim",
                )
        if not snap.disks:
            text.append("no disks", style="dim")
        self.update(text)


class NetworkPanel(Static):
    DEFAULT_CSS = """
    NetworkPanel { height: auto; padding: 1; border: round #5c588d; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._recv_history: deque[float] = deque(maxlen=40)
        self._send_history: deque[float] = deque(maxlen=40)

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        # aggregate rates for sparkline
        total_recv = sum(n.recv_rate for n in snap.network)
        total_send = sum(n.send_rate for n in snap.network)
        self._recv_history.append(total_recv)
        self._send_history.append(total_send)
        text = Text()
        for n in snap.network:
            state = "up" if n.is_up else "down"
            st = "green" if n.is_up else "red"
            text.append(f"{n.name} ", style="bold")
            text.append(f"({state})\n", style=st)
            text.append(
                f"  ↓ {human_rate(n.recv_rate):>14}   ↑ {human_rate(n.send_rate):>14}\n",
                style="dim",
            )
            text.append(
                f"  rx {human_bytes(n.bytes_recv)}  tx {human_bytes(n.bytes_sent)}\n",
                style="dim",
            )
        if not snap.network:
            text.append("no interfaces", style="dim")
        else:
            text.append(f"rx {sparkline(self._recv_history, 24)}\n", style="dim")
            text.append(f"tx {sparkline(self._send_history, 24)}\n", style="dim")
        self.update(text)


class GpuPanel(Static):
    DEFAULT_CSS = """
    GpuPanel { height: auto; padding: 1; border: round #4897d4; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        text = Text()
        if not snap.gpus:
            text.append("No GPU detected", style="dim")
            self.update(text)
            return
        for g in snap.gpus:
            if not g.available:
                text.append(f"{g.name}\n", style="dim")
                if g.error:
                    text.append(f"  {g.error}\n", style="red dim")
                continue
            text.append(f"{g.name}\n", style="bold")
            if g.utilization is not None:
                st = _usage_style(g.utilization, 90).split()[0]
                text.append(f"  util {g.utilization:5.1f}%  ", style=st)
                text.append(bar(g.utilization, 16), style=st)
                text.append("\n")
            if g.memory_used is not None and g.memory_total:
                pct = g.memory_used / g.memory_total * 100
                text.append(
                    f"  vram {human_bytes(g.memory_used)}/"
                    f"{human_bytes(g.memory_total)} ({pct:.0f}%)\n",
                    style="dim",
                )
            if g.temperature is not None:
                text.append(f"  temp {g.temperature:.1f}°C\n", style="dim")
        self.update(text)


class SensorsPanel(Static):
    DEFAULT_CSS = """
    SensorsPanel { height: auto; padding: 1; border: round #5c8d8d; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        text = Text()
        if not snap.sensors:
            text.append("no sensors", style="dim")
            self.update(text)
            return
        for s in snap.sensors:
            label = s.label or s.chip
            text.append(f"{s.chip}/{label}: ", style="bold")
            text.append(f"{s.current:.1f}")
            if s.high is not None:
                text.append(f"  (high {s.high:.0f})", style="dim")
            if s.current >= (s.critical or 1e9):
                text.append("  CRIT", style="red bold")
            elif s.high is not None and s.current >= s.high:
                text.append("  HIGH", style="yellow")
            text.append("\n")
        self.update(text)


class SystemInfoPanel(Static):
    DEFAULT_CSS = """
    SystemInfoPanel { height: auto; padding: 1; border: round #805252; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        info = get_system_info()
        text = Text()
        for key, val in info.items():
            text.append(f"{key:<24}", style="bold cyan")
            text.append(f"{val}\n")
        self.update(text)


class ProcessTable(DataTable):
    DEFAULT_CSS = """
    ProcessTable { height: 1fr; border: round $primary; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True

    def setup_columns(self, columns: list[str]) -> None:
        self.clear(columns=True)
        colmap = {
            "pid": ("PID", 8),
            "name": ("NAME", 22),
            "user": ("USER", 12),
            "cpu": ("CPU%", 7),
            "mem": ("MEM%", 7),
            "rss": ("RSS", 9),
            "status": ("STATUS", 10),
            "threads": ("THR", 5),
            "cmd": ("CMD", 40),
        }
        for c in columns:
            if c in colmap:
                name, width = colmap[c]
                self.add_column(name, width=width)

    def update_data(self, snap: SystemSnapshot, config: Config, filter_text: str = "") -> None:
        # rebuild rows
        self.clear()
        rows = snap.processes
        if filter_text:
            ft = filter_text.lower()
            rows = [
                r
                for r in rows
                if ft in r.name.lower()
                or ft in str(r.pid)
                or ft in r.username.lower()
                or ft in r.status.lower()
            ]
        # process tree depths
        depths: dict[int, int] = {}
        if getattr(config, "process_tree", False):
            by_pid = {r.pid: r for r in rows}
            for r in rows:
                d = 0
                cur = r.ppid
                seen = {r.pid}
                while cur in by_pid and cur not in seen and d < 10:
                    seen.add(cur)
                    d += 1
                    cur = by_pid[cur].ppid
                depths[r.pid] = d
        for r in rows:
            vals = []
            for c in config.process_columns:
                if c == "pid":
                    vals.append(str(r.pid))
                elif c == "name":
                    indent = "  " * depths.get(r.pid, 0)
                    vals.append((indent + r.name)[:22])
                elif c == "user":
                    vals.append(r.username[:12])
                elif c == "cpu":
                    vals.append(f"{r.cpu_percent:6.1f}")
                elif c == "mem":
                    vals.append(f"{r.memory_percent:6.1f}")
                elif c == "status":
                    vals.append(r.status[:10])
                elif c == "threads":
                    vals.append(str(r.num_threads))
                elif c == "cmd":
                    vals.append((r.cmdline or r.name)[:40])
                elif c == "rss":
                    vals.append(human_bytes(r.memory_rss))
            self.add_row(*vals, key=str(r.pid))


def _fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {mins}m"
    if hours:
        return f"{hours}h {mins}m {secs}s"
    return f"{mins}m {secs}s"


def _usage_style(value: float, threshold: float) -> str:
    if value >= threshold:
        return "red bold"
    if value >= 50:
        return "yellow"
    return "green"


def _fmt_time(ts: float) -> str:
    import datetime

    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
