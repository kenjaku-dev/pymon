"""Configuration loading/saving for pymon."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "sysmon" / "config.json"


@dataclass
class Thresholds:
    cpu: float = 85.0
    memory: float = 85.0
    disk: float = 90.0


@dataclass
class Config:
    refresh_interval: float = 1.0
    theme: str = "dark"
    process_sort: str = "cpu"
    process_sort_desc: bool = True
    process_row_cap: int = 50
    process_columns: list[str] = field(
        default_factory=lambda: ["pid", "name", "cpu", "mem", "status"]
    )
    thresholds: Thresholds = field(default_factory=Thresholds)
    show_all_interfaces: bool = True
    show_all_partitions: bool = False
    process_tree: bool = False

    def clamped_interval(self) -> float:
        return max(0.1, min(10.0, self.refresh_interval))


def _default_config() -> Config:
    return Config()


def load_config(path: Path | None = None) -> Config:
    target = path if path is not None else CONFIG_PATH
    if not target.exists():
        cfg = _default_config()
        save_config(cfg, target)
        return cfg
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_config()
    cfg = _default_config()
    cfg.refresh_interval = float(raw.get("refresh_interval", cfg.refresh_interval))
    cfg.theme = str(raw.get("theme", cfg.theme))
    cfg.process_sort = str(raw.get("process_sort", cfg.process_sort))
    cfg.process_sort_desc = bool(raw.get("process_sort_desc", cfg.process_sort_desc))
    cfg.process_row_cap = int(raw.get("process_row_cap", cfg.process_row_cap))
    if isinstance(raw.get("process_columns"), list):
        cfg.process_columns = [str(x) for x in raw["process_columns"]]
    thr = raw.get("thresholds")
    if isinstance(thr, dict):
        cfg.thresholds = Thresholds(
            cpu=float(thr.get("cpu", cfg.thresholds.cpu)),
            memory=float(thr.get("memory", cfg.thresholds.memory)),
            disk=float(thr.get("disk", cfg.thresholds.disk)),
        )
    cfg.show_all_interfaces = bool(raw.get("show_all_interfaces", cfg.show_all_interfaces))
    cfg.show_all_partitions = bool(raw.get("show_all_partitions", cfg.show_all_partitions))
    cfg.process_tree = bool(raw.get("process_tree", cfg.process_tree))
    cfg.refresh_interval = cfg.clamped_interval()
    return cfg


def save_config(config: Config, path: Path | None = None) -> None:
    target = path if path is not None else CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")