"""Tests for utils helpers."""

from pymon.utils import bar, human_bytes, sparkline


def test_bar_bounds() -> None:
    assert bar(0, 5) == "░" * 5
    assert bar(100, 5) == "█" * 5
    assert len(bar(50, 10)) == 10


def test_human_bytes() -> None:
    assert "KiB" in human_bytes(1024)
    assert "B" in human_bytes(5)


def test_sparkline_empty() -> None:
    assert sparkline([]) == ""


def test_sparkline_length() -> None:
    out = sparkline([1.0, 2.0, 3.0, 4.0], width=8)
    assert len(out) == 8
    assert out.strip() != ""
