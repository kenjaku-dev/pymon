"""Data models for collected system metrics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CpuInfo:
    overall: float = 0.0
    per_core: list[float] = field(default_factory=list)
    freq_mhz: float | None = None
    load_avg: tuple[float, float, float] | None = None
    temp_c: float | None = None


@dataclass
class MemInfo:
    total: int = 0
    used: int = 0
    available: int = 0
    percent: float = 0.0
    swap_total: int = 0
    swap_used: int = 0
    swap_percent: float = 0.0


@dataclass
class DiskPartition:
    device: str = ""
    mountpoint: str = ""
    fstype: str = ""
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0


@dataclass
class DiskIO:
    read_bytes: int = 0
    write_bytes: int = 0
    read_rate: float = 0.0
    write_rate: float = 0.0


@dataclass
class NetInterface:
    name: str = ""
    bytes_sent: int = 0
    bytes_recv: int = 0
    send_rate: float = 0.0
    recv_rate: float = 0.0
    is_up: bool = True


@dataclass
class ProcessInfo:
    pid: int = 0
    name: str = ""
    username: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    status: str = ""
    num_threads: int = 0


@dataclass
class SensorReading:
    chip: str = ""
    label: str = ""
    current: float = 0.0
    high: float | None = None
    critical: float | None = None


@dataclass
class GpuInfo:
    name: str = ""
    utilization: float | None = None
    memory_used: int | None = None
    memory_total: int | None = None
    temperature: float | None = None
    available: bool = True
    error: str | None = None


@dataclass
class SystemSnapshot:
    timestamp: float = 0.0
    hostname: str = ""
    uptime_seconds: float = 0.0
    cpu: CpuInfo = field(default_factory=CpuInfo)
    memory: MemInfo = field(default_factory=MemInfo)
    disks: list[DiskPartition] = field(default_factory=list)
    disk_io: DiskIO | None = None
    network: list[NetInterface] = field(default_factory=list)
    processes: list[ProcessInfo] = field(default_factory=list)
    sensors: list[SensorReading] = field(default_factory=list)
    gpus: list[GpuInfo] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)