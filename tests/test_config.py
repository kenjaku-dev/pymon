"""Tests for config module."""

from __future__ import annotations

import json
from pathlib import Path

from pymon.config import Config, load_config, save_config


def test_default_config_created(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = load_config(cfg_path)
    assert cfg.refresh_interval == 1.0
    assert cfg.theme == "dark"
    assert cfg_path.exists()


def test_save_and_reload(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = Config(refresh_interval=2.5, theme="light", process_row_cap=10)
    save_config(cfg, cfg_path)
    loaded = load_config(cfg_path)
    assert loaded.refresh_interval == 2.5
    assert loaded.theme == "light"
    assert loaded.process_row_cap == 10


def test_clamped_interval(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"refresh_interval": 100.0}), encoding="utf-8")
    loaded = load_config(cfg_path)
    assert loaded.refresh_interval == 10.0

    cfg_path.write_text(json.dumps({"refresh_interval": 0.01}), encoding="utf-8")
    loaded = load_config(cfg_path)
    assert loaded.refresh_interval == 0.1


def test_corrupt_config_falls_back(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("{not json", encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.refresh_interval == 1.0


def test_process_tree_roundtrip(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg = Config(process_tree=True, last_tab="processes-tab")
    save_config(cfg, cfg_path)
    loaded = load_config(cfg_path)
    assert loaded.process_tree is True
    assert loaded.last_tab == "processes-tab"
