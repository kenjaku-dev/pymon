# pymon — Project Context

## Overview
`pymon` is a Linux system monitor TUI built with `psutil` and `Textual`. It displays CPU, memory, disk, network, processes, sensors, GPU, and static system info in a tabbed terminal dashboard. Single-package Python project, MIT licensed, Python >= 3.12.

## Repository layout
```
pymon/
├── pyproject.toml          # build, deps, ruff/pyright/pytest config
├── README.md
├── install.sh              # installs into ~/.local/share/pymon/venv
├── context.md              # this file
├── docs/index.html         # landing page (GitHub Pages)
├── src/pymon/
│   ├── __init__.py         # __version__ = "0.1.0"
│   ├── __main__.py         # CLI entry point (argparse -> PymonApp)
│   ├── app.py              # Textual App, keybindings, modals, tick loop
│   ├── config.py           # Config dataclass + load/save JSON
│   ├── utils.py            # human_bytes, human_rate, bar
│   ├── collectors/
│   │   ├── __init__.py     # exports SystemCollector (+ models *)
│   │   ├── models.py       # dataclasses: CpuInfo, MemInfo, ..., SystemSnapshot
│   │   └── system.py       # SystemCollector + collect_system_info()
│   └── ui/
│       ├── __init__.py
│       └── panels.py       # Textual widgets (panels + ProcessTable)
└── tests/
    ├── test_app.py
    ├── test_collectors.py
    └── test_config.py
```

## Architecture
- **Entry:** `pymon.__main__:main` builds an argparse parser, loads config, applies CLI overrides, runs `PymonApp`.
- **App (`app.py`):** Textual `App` with 3 tabs (overview grid, processes, system info). A `set_interval` tick calls `SystemCollector.collect` in a worker thread, then `_apply` updates all widgets. Supports pause, force refresh, filtering, sorting, kill process (SIGTERM/SIGKILL with confirm modal).
- **Config (`config.py`):** dataclass `Config` persisted to `~/.config/sysmon/config.json` (or `--config`). `Thresholds` nested. `clamped_interval()` clamps 0.1–10.0.
- **Collectors (`collectors/system.py`):** stateful `SystemCollector` computes rates between calls (`_prev_disk`, `_prev_net`). Wraps each subsystem in try/except, recording errors in `snap.errors`. Optional GPU via `pynvml` (`pip install pymon[gpu]`).
- **UI (`ui/panels.py`):** `Static` subclasses rendering `rich.text.Text`; `ProcessTable(DataTable)`. Helpers `_fmt_uptime`, `_usage_style`, `_fmt_time`.

## Key commands
```bash
# install (editable) into a venv
pip install -e .
pip install -e ".[gpu]"      # optional GPU
pip install -e ".[dev]"      # pytest, ruff, pyright

# run
pymon
pymon --refresh 0.5 --theme light --sort mem --desc --rows 100
pymon --config /path/to/config.json

# tests / lint / types
pytest
ruff check .
ruff format --check .
pyright
```

Config dir: `~/.config/sysmon/`. Logs: `~/.local/share/pymon/pymon.log`.

## Conventions
- Source under `src/`; tests under `tests/`; `pythonpath = ["src"]` for pytest.
- Ruff: line-length 100, target py312, rules `E F I B UP SIM`.
- Pyright: standard mode, python 3.12, venv `.venv`.
- Data flow: collector returns `SystemSnapshot`; panels receive `(snap, config)`.
- Process sort keys: `cpu`, `mem`, `pid`, `name`; columns configurable via `process_columns`.
- Keep Arabic/RTL rules from global AGENTS.md when responding in Arabic.

## Known gotchas
- `.venv` may need repointing to the real venv (`~/.local/share/pymon/venv`).
- `pynvml` is optional; GPU panel shows "not installed" message otherwise.
- `_collecting` flag guards collection concurrency; `_apply` runs on UI thread via `call_from_thread`.
- `ProcessTable._selected_pid` uses `ordered_rows[cursor_row].key.value` (pid stored as row key).

## Current version
0.1.0 (matches `__init__.__version__` and CLI `--version`).