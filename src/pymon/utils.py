"""Formatting helpers."""

from __future__ import annotations

from collections.abc import Sequence


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


_SPARK_BLOCKS = " ▂▃▄▅▆▇█"


def sparkline(values: Sequence[float], width: int = 24) -> str:
    """Render a compact unicode sparkline for ``values`` (last ``width`` kept)."""
    vals = list(values)[-width:]
    if not vals:
        return ""
    lo = min(vals)
    hi = max(vals)
    span = hi - lo if hi != lo else 1.0
    out = []
    for v in vals:
        idx = int((v - lo) / span * (len(_SPARK_BLOCKS) - 1))
        idx = max(0, min(len(_SPARK_BLOCKS) - 1, idx))
        out.append(_SPARK_BLOCKS[idx])
    # pad left so width stays stable
    if len(out) < width:
        out = [" "] * (width - len(out)) + out
    return "".join(out)