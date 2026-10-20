# pymon

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](#)

A fast, beautiful **Linux system monitor TUI** built with [`psutil`](https://github.com/giampaolo/psutil) and [`Textual`](https://github.com/Textualize/textual). CPU, memory, disk, network, processes, sensors, GPU, and static system info — all in one terminal dashboard.

## ✨ Features

- **Overview tab** — CPU (overall + per-core, freq, temp), RAM/swap, disks with usage bars, network I/O rates, GPU, sensors.
- **Processes tab** — sortable, filterable process table (PID, name, user, CPU%, MEM%, status, threads).
- **System Info tab** — hostname, OS, CPU model/cores, memory, disks, uptime, load average, etc.
- **Live refresh** with adjustable interval (`+`/`-`), pause/resume.
- **Process management** — kill selected process (SIGTERM / SIGKILL) with confirmation.
- **Configurable** thresholds, columns, row cap, refresh interval, theme.
- **Optional NVIDIA GPU** support via `nvidia-ml-py`.
- **Keyboard-driven** — no mouse required.

## 📦 Install

### Quick install (recommended)

```bash
git clone https://github.com/kenjaku-dev/pymon.git
cd pymon
./install.sh
```

The script creates a venv at `~/.local/share/pymon/venv`, installs dependencies, and symlinks `pymon` into `~/.local/bin`.

Optional flags:

```bash
PYMON_GPU=1 ./install.sh       # install NVIDIA GPU support
PYMON_DEV=1 ./install.sh       # also install pytest/ruff/pyright
PYMON_VENV=/custom/venv PYMON_BIN=/custom/bin ./install.sh
```

### Manual / developer install

```bash
pip install -e .
# optional GPU support
pip install -e ".[gpu]"
# dev tools
pip install -e ".[dev]"
```

Requires Python **3.12+** and Linux.

## 🚀 Run

```bash
pymon
```

Make sure `~/.local/bin` is on your `PATH` (added by most distros; otherwise add it in your shell rc).

## ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `p` | Pause / resume refresh |
| `r` | Force refresh |
| `k` / `K` | Kill selected process (SIGTERM / SIGKILL) |
| `/` | Filter processes |
| `s` | Cycle sort column (cpu → mem → pid → name) |
| `a` | Toggle sort direction (asc/desc) |
| `+` / `-` | Faster / slower refresh |
| `1` / `2` / `3` | Switch tabs (overview / processes / system info) |
| `Tab` | Next tab |
| `h` | Help |
| `Esc` | Close modal / clear filter |

## ⚙️ CLI options

```text
pymon [--config PATH] [--refresh SEC] [--theme {dark,light}]
      [--sort {cpu,mem,pid,name}] [--desc] [--asc] [--rows N] [--version]
```

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to a config JSON file |
| `--refresh SEC` | Refresh interval (clamped 0.1–10.0) |
| `--theme {dark,light}` | Color theme |
| `--sort {cpu,mem,pid,name}` | Process sort column |
| `--desc` / `--asc` | Sort direction |
| `--rows N` | Max process rows |
| `--version` | Print version and exit |

## 🔧 Configuration

Created automatically at `~/.config/sysmon/config.json` on first run. Override via CLI flags. Example:

```json
{
  "refresh_interval": 1.0,
  "theme": "dark",
  "process_sort": "cpu",
  "process_sort_desc": true,
  "process_row_cap": 50,
  "process_columns": ["pid", "name", "cpu", "mem", "status"],
  "thresholds": { "cpu": 85.0, "memory": 85.0, "disk": 90.0 },
  "show_all_interfaces": true,
  "show_all_partitions": false
}
```

| Field | Description |
|-------|-------------|
| `refresh_interval` | Seconds between refreshes (0.1–10.0) |
| `theme` | `dark` or `light` |
| `process_sort` / `process_sort_desc` | Default sort column and direction |
| `process_row_cap` | Max process rows collected |
| `process_columns` | Columns to display: `pid`, `name`, `user`, `cpu`, `mem`, `status`, `threads`, `cmd` |
| `thresholds.cpu/memory/disk` | Percent at which bars turn red |
| `show_all_interfaces` | Include loopback and all interfaces |
| `show_all_partitions` | Include pseudo/virtual filesystems |

## 🧪 Development

```bash
pytest                      # run tests
ruff check .                # lint
ruff format --check .       # format check
pyright                     # type check
```

Tests live in `tests/`; source under `src/pymon/`.

## 🐛 Troubleshooting

- **`pymon: command not found`** — ensure `~/.local/bin` is on `PATH`, or run `~/.local/share/pymon/venv/bin/pymon`.
- **No GPU info** — install optional dependency: `pip install "pymon[gpu]"` (or `PYMON_GPU=1 ./install.sh`).
- **Permission errors killing processes** — run with appropriate privileges (e.g. `sudo`) for processes owned by other users.
- **Config corrupted** — delete `~/.config/sysmon/config.json`; it will be regenerated with defaults.

## 📄 License

MIT — see [LICENSE](LICENSE).