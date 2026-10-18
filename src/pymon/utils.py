"""Formatting helpers."""

from __future__ import annotations


def human_bytes(n: int | float) -> str:
    n = float(n)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}"
        n /= 1024.0
    return f"{n:6.1f} PiB"


def human_rate(bps: float) -> str:
    return human_bytes(bps) + "/s"


def bar(percent: float, width: int = 20) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(round(percent / 100.0 * width))
    return "█" * filled + "░" * (width - filled)