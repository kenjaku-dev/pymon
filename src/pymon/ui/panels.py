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
        t = Text()
        t.append(f"{snap.hostname}", style="bold cyan")
        t.append("  │  up ")
        t.append(_fmt_uptime(snap.uptime_seconds), style="green")
        if snap.cpu.load_avg:
            la = snap.cpu.load_avg
            t.append(f"  │  load {la[0]:.2f} {la[1]:.2f} {la[2]:.2f}")
        t.append(f"  │  {snap.timestamp and _fmt_time(snap.timestamp)}")
        if snap.errors:
            t.append(f"  │  errors: {len(snap.errors)}", style="red")
        self.update(t)


class CpuPanel(Static):
    DEFAULT_CSS = """
    CpuPanel { height: auto; padding: 1; border: round #556d59; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=40)

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        cpu = snap.cpu
        thr = config.thresholds.cpu
        self._history.append(cpu.overall)
        t = Text()
        style = _usage_style(cpu.overall, thr)
        t.append(f"CPU  {cpu.overall:5.1f}%  ", style=style)
        t.append(bar(cpu.overall, 18), style=style.split()[0])
        if cpu.overall >= thr:
            t.append("  ⚠", style="red bold")
        t.append("\n")
        t.append(f"hist {sparkline(self._history, 24)}\n", style="dim")
        if cpu.freq_mhz:
            t.append(f"freq {cpu.freq_mhz:7.0f} MHz   ", style="dim")
        if cpu.temp_c is not None:
            t.append(f"temp {cpu.temp_c:4.1f}°C", style="dim")
        t.append("\n")
        # per-core
        cores = cpu.per_core
        for i, c in enumerate(cores):
            st = _usage_style(c, thr).split()[0]
            t.append(f"c{i:<2} {c:5.1f}% ", style=st)
            t.append(bar(c, 10), style=st)
            if (i + 1) % 2 == 0:
                t.append("\n")
            else:
                t.append("  ")
        if len(cores) % 2:
            t.append("\n")
        self.update(t)


class MemoryPanel(Static):
    DEFAULT_CSS = """
    MemoryPanel { height: auto; padding: 1; border: round #6c6c4b; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=40)

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        m = snap.memory
        thr = config.thresholds.memory
        self._history.append(m.percent)
        t = Text()
        st = _usage_style(m.percent, thr)
        t.append(f"RAM  {m.percent:5.1f}%  ", style=st)
        t.append(bar(m.percent, 18), style=st.split()[0])
        if m.percent >= thr:
            t.append("  ⚠", style="red bold")
        t.append("\n")
        t.append(f"hist {sparkline(self._history, 24)}\n", style="dim")
        t.append(
            f"{human_bytes(m.used)} / {human_bytes(m.total)}   avail {human_bytes(m.available)}\n",
            style="dim",
        )
        # swap
        ss = _usage_style(m.swap_percent, thr).split()[0]
        t.append(f"SWAP {m.swap_percent:5.1f}%  ", style=ss)
        t.append(bar(m.swap_percent, 18), style=ss)
        t.append("\n")
        t.append(f"{human_bytes(m.swap_used)} / {human_bytes(m.swap_total)}", style="dim")
        self.update(t)


class DiskPanel(Static):
    DEFAULT_CSS = """
    DiskPanel { height: auto; padding: 1; border: round #8a6d3b; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        thr = config.thresholds.disk
        t = Text()
        for d in sorted(snap.disks, key=lambda x: x.mountpoint):
            st = _usage_style(d.percent, thr)
            t.append(f"{d.mountpoint}", style="bold")
            t.append(f"  ({d.device}, {d.fstype})\n", style="dim")
            t.append(f"  {d.percent:5.1f}%  ", style=st)
            t.append(bar(d.percent, 20), style=st.split()[0])
            t.append(f"  {human_bytes(d.used)}/{human_bytes(d.total)}\n", style="dim")
        if snap.disk_io is not None:
            dio = snap.disk_io
            t.append(
                f"IO  R {human_rate(dio.read_rate)}  W {human_rate(dio.write_rate)}",
                style="dim",
            )
        if getattr(snap, "disk_io_per_device", None):
            for dev in sorted(snap.disk_io_per_device)[:5]:
                dio = snap.disk_io_per_device[dev]
                t.append(
                    f"  {dev}: R {human_rate(dio.read_rate)}  W {human_rate(dio.write_rate)}\n",
                    style="dim",
                )
        if not snap.disks:
            t.append("no disks", style="dim")
        self.update(t)


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
        t = Text()
        for n in snap.network:
            state = "up" if n.is_up else "down"
            st = "green" if n.is_up else "red"
            t.append(f"{n.name} ", style="bold")
            t.append(f"({state})\n", style=st)
            t.append(
                f"  ↓ {human_rate(n.recv_rate):>14}   ↑ {human_rate(n.send_rate):>14}\n",
                style="dim",
            )
            t.append(
                f"  rx {human_bytes(n.bytes_recv)}  tx {human_bytes(n.bytes_sent)}\n",
                style="dim",
            )
        if not snap.network:
            t.append("no interfaces", style="dim")
        else:
            t.append(f"rx {sparkline(self._recv_history, 24)}\n", style="dim")
            t.append(f"tx {sparkline(self._send_history, 24)}\n", style="dim")
        self.update(t)


class GpuPanel(Static):
    DEFAULT_CSS = """
    GpuPanel { height: auto; padding: 1; border: round #4897d4; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        t = Text()
        if not snap.gpus:
            t.append("No GPU detected", style="dim")
            self.update(t)
            return
        for g in snap.gpus:
            if not g.available:
                t.append(f"{g.name}\n", style="dim")
                if g.error:
                    t.append(f"  {g.error}\n", style="red dim")
                continue
            t.append(f"{g.name}\n", style="bold")
            if g.utilization is not None:
                st = _usage_style(g.utilization, 90).split()[0]
                t.append(f"  util {g.utilization:5.1f}%  ", style=st)
                t.append(bar(g.utilization, 16), style=st)
                t.append("\n")
            if g.memory_used is not None and g.memory_total:
                pct = g.memory_used / g.memory_total * 100
                t.append(
                    f"  vram {human_bytes(g.memory_used)}/"
                    f"{human_bytes(g.memory_total)} ({pct:.0f}%)\n",
                    style="dim",
                )
            if g.temperature is not None:
                t.append(f"  temp {g.temperature:.1f}°C\n", style="dim")
        self.update(t)


class SensorsPanel(Static):
    DEFAULT_CSS = """
    SensorsPanel { height: auto; padding: 1; border: round #5c8d8d; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        t = Text()
        if not snap.sensors:
            t.append("no sensors", style="dim")
            self.update(t)
            return
        for s in snap.sensors:
            label = s.label or s.chip
            t.append(f"{s.chip}/{label}: ", style="bold")
            t.append(f"{s.current:.1f}")
            if s.high is not None:
                t.append(f"  (high {s.high:.0f})", style="dim")
            if s.current >= (s.critical or 1e9):
                t.append("  CRIT", style="red bold")
            elif s.high is not None and s.current >= s.high:
                t.append("  HIGH", style="yellow")
            t.append("\n")
        self.update(t)


class SystemInfoPanel(Static):
    DEFAULT_CSS = """
    SystemInfoPanel { height: auto; padding: 1; border: round #805252; }
    """

    def update_data(self, snap: SystemSnapshot, config: Config) -> None:
        info = get_system_info()
        t = Text()
        for key, val in info.items():
            t.append(f"{key:<24}", style="bold cyan")
            t.append(f"{val}\n")
        self.update(t)


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
