"""Collect system metrics into a SystemSnapshot."""

from __future__ import annotations

import contextlib
import logging
import os
import platform
import socket
import time

import psutil

from .models import (
    CpuInfo,
    DiskIO,
    DiskPartition,
    GpuInfo,
    MemInfo,
    NetInterface,
    ProcessInfo,
    SensorReading,
    SystemSnapshot,
)

logger = logging.getLogger("pymon.collectors")

_PSEUDO_FS = {
    "proc", "sysfs", "devtmpfs", "devpts", "cgroup", "cgroup2", "pstore", "bpf",
    "tracefs", "debugfs", "securityfs", "configfs", "fusectl", "mqueue", "hugetlbfs", "ramfs",
}


class SystemCollector:
    """Stateful collector that computes rates between calls."""

    def __init__(self) -> None:
        # prime cpu percent
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)
        self._prev_disk: tuple[int, int, float] | None = None  # read, write, ts
        self._prev_net: dict[str, tuple[int, int, float]] = {}
        self._prev_ts: float = time.time()

    def collect(self, process_row_cap: int = 50, process_sort: str = "cpu",
                process_sort_desc: bool = True, show_all_interfaces: bool = True,
                show_all_partitions: bool = True) -> SystemSnapshot:
        snap = SystemSnapshot(timestamp=time.time())
        snap.hostname = socket.gethostname()
        try:
            snap.uptime_seconds = time.time() - psutil.boot_time()
        except Exception as e:  # pragma: no cover
            snap.errors["uptime"] = str(e)
            logger.warning("uptime collection failed: %s", e)

        # CPU
        try:
            snap.cpu = self._collect_cpu()
        except Exception as e:
            snap.errors["cpu"] = str(e)
            logger.warning("cpu collection failed: %s", e)

        # Memory
        try:
            snap.memory = self._collect_memory()
        except Exception as e:
            snap.errors["memory"] = str(e)
            logger.warning("memory collection failed: %s", e)

        # Disk
        try:
            snap.disks = self._collect_disks(show_all_partitions)
            snap.disk_io = self._collect_disk_io()
        except Exception as e:
            snap.errors["disk"] = str(e)
            logger.warning("disk collection failed: %s", e)

        # Network
        try:
            snap.network = self._collect_network(show_all_interfaces)
        except Exception as e:
            snap.errors["network"] = str(e)
            logger.warning("network collection failed: %s", e)

        # Processes
        try:
            snap.processes = self._collect_processes(
                process_row_cap, process_sort, process_sort_desc
            )
        except Exception as e:
            snap.errors["processes"] = str(e)
            logger.warning("processes collection failed: %s", e)

        # Sensors
        try:
            snap.sensors = self._collect_sensors()
        except Exception as e:
            snap.errors["sensors"] = str(e)
            logger.warning("sensors collection failed: %s", e)

        # GPU
        try:
            snap.gpus = self._collect_gpu()
        except Exception as e:
            snap.errors["gpu"] = str(e)
            logger.warning("gpu collection failed: %s", e)

        return snap

    # ---- individual collectors ----

    def _collect_cpu(self) -> CpuInfo:
        info = CpuInfo()
        info.overall = float(psutil.cpu_percent(interval=None))
        info.per_core = [float(x) for x in psutil.cpu_percent(interval=None, percpu=True)]
        try:
            freq = psutil.cpu_freq()
            if freq is not None:
                info.freq_mhz = float(freq.current)
        except Exception:
            pass
        try:
            la = psutil.getloadavg()
            info.load_avg = (float(la[0]), float(la[1]), float(la[2]))
        except (AttributeError, OSError):
            info.load_avg = None
        # temperature
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # prefer cpu-ish keys
                for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    if key in temps and temps[key]:
                        info.temp_c = float(temps[key][0].current)
                        break
                if info.temp_c is None:
                    # fallback first
                    first = next(iter(temps.values()))
                    if first:
                        info.temp_c = float(first[0].current)
        except Exception:
            info.temp_c = None
        return info

    def _collect_memory(self) -> MemInfo:
        vm = psutil.virtual_memory()
        sm = psutil.swap_memory()
        return MemInfo(
            total=int(vm.total),
            used=int(vm.used),
            available=int(vm.available),
            percent=float(vm.percent),
            swap_total=int(sm.total),
            swap_used=int(sm.used),
            swap_percent=float(sm.percent),
        )

    def _collect_disks(self, show_all: bool) -> list[DiskPartition]:
        result: list[DiskPartition] = []
        if show_all:
            try:
                parts = psutil.disk_partitions(all=True)
            except Exception:
                parts = psutil.disk_partitions(all=False)
        else:
            # physical disks only (important partitions)
            try:
                parts = psutil.disk_partitions(all=False)
            except Exception:
                parts = psutil.disk_partitions(all=True)
        for p in parts:
            if p.fstype.lower() in ("proc", "sysfs", "devtmpfs", "devpts"):
                continue
            if not show_all and p.fstype.lower() in _PSEUDO_FS:
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
            except (PermissionError, OSError):
                continue
            result.append(
                DiskPartition(
                    device=p.device,
                    mountpoint=p.mountpoint,
                    fstype=p.fstype,
                    total=int(usage.total),
                    used=int(usage.used),
                    free=int(usage.free),
                    percent=float(usage.percent),
                )
            )
        return result

    def _collect_disk_io(self) -> DiskIO | None:
        try:
            io = psutil.disk_io_counters()
        except Exception:
            return None
        if io is None:
            return None
        now = time.time()
        read_rate = 0.0
        write_rate = 0.0
        if self._prev_disk is not None:
            prev_r, prev_w, prev_ts = self._prev_disk
            dt = now - prev_ts
            if dt > 0:
                read_rate = max(0.0, (io.read_bytes - prev_r) / dt)
                write_rate = max(0.0, (io.write_bytes - prev_w) / dt)
        self._prev_disk = (int(io.read_bytes), int(io.write_bytes), now)
        return DiskIO(
            read_bytes=int(io.read_bytes),
            write_bytes=int(io.write_bytes),
            read_rate=read_rate,
            write_rate=write_rate,
        )

    def _collect_network(self, show_all: bool) -> list[NetInterface]:
        result: list[NetInterface] = []
        try:
            stats = psutil.net_if_stats()
        except Exception:
            stats = {}
        try:
            counters = psutil.net_io_counters(pernic=True)
        except Exception:
            counters = {}
        now = time.time()
        for name, c in counters.items():
            is_up = True
            if name in stats:
                is_up = bool(stats[name].isup)
            # rates
            send_rate = 0.0
            recv_rate = 0.0
            prev = self._prev_net.get(name)
            if prev is not None:
                prev_s, prev_r, prev_ts = prev
                dt = now - prev_ts
                if dt > 0:
                    send_rate = max(0.0, (c.bytes_sent - prev_s) / dt)
                    recv_rate = max(0.0, (c.bytes_recv - prev_r) / dt)
            self._prev_net[name] = (int(c.bytes_sent), int(c.bytes_recv), now)
            if not show_all and name == "lo":
                # user said show all, but keep flag respected
                pass
            result.append(
                NetInterface(
                    name=name,
                    bytes_sent=int(c.bytes_sent),
                    bytes_recv=int(c.bytes_recv),
                    send_rate=send_rate,
                    recv_rate=recv_rate,
                    is_up=is_up,
                )
            )
        # filter loopback only if not show_all
        if not show_all:
            result = [n for n in result if n.name != "lo"]
        return result

    def _collect_processes(self, cap: int, sort: str, desc: bool) -> list[ProcessInfo]:
        rows: list[ProcessInfo] = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent",
                                     "memory_percent", "status", "num_threads"]):
            try:
                info = p.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            rows.append(
                ProcessInfo(
                    pid=int(info.get("pid") or 0),
                    name=str(info.get("name") or ""),
                    username=str(info.get("username") or ""),
                    cpu_percent=float(info.get("cpu_percent") or 0.0),
                    memory_percent=float(info.get("memory_percent") or 0.0),
                    status=str(info.get("status") or ""),
                    num_threads=int(info.get("num_threads") or 0),
                )
            )
        keymap = {
            "cpu": lambda x: x.cpu_percent,
            "mem": lambda x: x.memory_percent,
            "pid": lambda x: x.pid,
            "name": lambda x: x.name.lower(),
        }
        keyfn = keymap.get(sort, keymap["cpu"])
        rows.sort(key=keyfn, reverse=desc)
        return rows[:cap]

    def _collect_sensors(self) -> list[SensorReading]:
        out: list[SensorReading] = []
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
            temps = {}
        for chip, entries in (temps or {}).items():
            for e in entries:
                out.append(
                    SensorReading(
                        chip=chip,
                        label=getattr(e, "label", "") or chip,
                        current=float(e.current),
                        high=getattr(e, "high", None),
                        critical=getattr(e, "critical", None),
                    )
                )
        # fans
        try:
            fans = psutil.sensors_fans()
        except Exception:
            fans = {}
        for chip, entries in (fans or {}).items():
            for e in entries:
                out.append(
                    SensorReading(
                        chip=chip,
                        label=getattr(e, "label", "") or "fan",
                        current=float(e.current),
                        high=None,
                        critical=None,
                    )
                )
        return out

    def _collect_gpu(self) -> list[GpuInfo]:
        # try nvidia
        try:
            import pynvml  # type: ignore
        except Exception:
            return [GpuInfo(name="No GPU detected", available=False,
                            error="pynvml not installed (optional: pip install pymon[gpu])")]
        try:
            pynvml.nvmlInit()
        except Exception as e:
            return [GpuInfo(name="No GPU detected", available=False, error=str(e))]
        gpus: list[GpuInfo] = []
        try:
            count = pynvml.nvmlDeviceGetCount()
            if count == 0:
                return [GpuInfo(name="No GPU detected", available=False)]
            for i in range(count):
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(h)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", "replace")
                util = None
                mem_used = None
                mem_total = None
                temp = None
                try:
                    u = pynvml.nvmlDeviceGetUtilizationRates(h)
                    util = float(u.gpu)
                except Exception:
                    pass
                try:
                    m = pynvml.nvmlDeviceGetMemoryInfo(h)
                    mem_used = int(m.used)
                    mem_total = int(m.total)
                except Exception:
                    pass
                with contextlib.suppress(Exception):
                    temp = float(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
                gpus.append(GpuInfo(name=name, utilization=util, memory_used=mem_used,
                                    memory_total=mem_total, temperature=temp, available=True))
        except Exception as e:
            gpus.append(GpuInfo(name="GPU error", available=False, error=str(e)))
        finally:
            with contextlib.suppress(Exception):
                pynvml.nvmlShutdown()
        return gpus if gpus else [GpuInfo(name="No GPU detected", available=False)]


def collect_system_info() -> dict[str, str]:
    """Collect static system information for the System Info panel."""
    info: dict[str, str] = {}
    info["Hostname"] = socket.gethostname()
    try:
        info["FQDN"] = socket.getfqdn()
    except Exception:
        info["FQDN"] = "-"
    info["OS"] = f"{platform.system()} {platform.release()}"
    info["OS version"] = platform.version()
    info["Architecture"] = platform.machine()
    info["Processor"] = platform.processor() or "-"
    # CPU model from /proc/cpuinfo
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    info["CPU model"] = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    info["CPU cores (physical)"] = str(psutil.cpu_count(logical=False) or 0)
    info["CPU cores (logical)"] = str(psutil.cpu_count(logical=True) or 0)
    try:
        freq = psutil.cpu_freq()
        if freq is not None:
            info["CPU frequency"] = f"{freq.current:.0f} MHz (max {freq.max:.0f})"
    except Exception:
        pass
    vm = psutil.virtual_memory()
    info["Memory total"] = _human_bytes(vm.total)
    info["Memory available"] = _human_bytes(vm.available)
    sm = psutil.swap_memory()
    info["Swap total"] = _human_bytes(sm.total)
    # disks
    try:
        parts = psutil.disk_partitions(all=False)
        total = sum(
            psutil.disk_usage(p.mountpoint).total
            for p in parts
            if _safe_usage(p.mountpoint)
        )
        info["Disks"] = f"{len(parts)} partitions, {_human_bytes(total)} total"
    except Exception:
        info["Disks"] = "-"
    # network interfaces
    try:
        info["Network interfaces"] = str(len(psutil.net_if_addrs()))
    except Exception:
        info["Network interfaces"] = "-"
    with contextlib.suppress(Exception):
        bt = psutil.boot_time()
        import datetime

        info["Boot time"] = datetime.datetime.fromtimestamp(bt).strftime("%Y-%m-%d %H:%M:%S")
    with contextlib.suppress(Exception):
        info["Uptime"] = _fmt_uptime(time.time() - psutil.boot_time())
    with contextlib.suppress(AttributeError, OSError):
        info["Load average"] = ", ".join(f"{x:.2f}" for x in psutil.getloadavg())
    info["User"] = os.environ.get("USER") or os.getlogin() if hasattr(os, "getlogin") else "-"
    info["Python"] = platform.python_version()
    return info


def _human_bytes(n: int | float) -> str:
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PiB"


def _safe_usage(path: str) -> bool:
    try:
        psutil.disk_usage(path)
        return True
    except Exception:
        return False


def _fmt_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {mins}m"
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m"