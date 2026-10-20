"""Tests for collectors."""

from __future__ import annotations

from pymon.collectors import SystemCollector


def test_collect_returns_snapshot() -> None:
    collector = SystemCollector()
    snap = collector.collect(process_row_cap=5)
    assert snap.hostname
    assert snap.timestamp > 0
    assert len(snap.processes) <= 5


def test_collect_twice_has_cpu() -> None:
    collector = SystemCollector()
    collector.collect(process_row_cap=3)
    snap = collector.collect(process_row_cap=3)
    # cpu overall should be a number 0..100
    assert 0.0 <= snap.cpu.overall <= 100.0
    assert len(snap.cpu.per_core) >= 1


def test_memory_positive() -> None:
    collector = SystemCollector()
    snap = collector.collect(process_row_cap=1)
    assert snap.memory.total > 0
    assert 0.0 <= snap.memory.percent <= 100.0


def test_network_interfaces() -> None:
    collector = SystemCollector()
    snap = collector.collect(process_row_cap=1)
    assert isinstance(snap.network, list)


def test_sensors_list() -> None:
    collector = SystemCollector()
    snap = collector.collect(process_row_cap=1)
    assert isinstance(snap.sensors, list)
