# pymon

A Linux system monitor TUI built with `psutil` and `textual`.

## Install

```bash
pip install -e .
# optional GPU support
pip install -e ".[gpu]"
```

## Run

```bash
pymon
```

## Config

Created automatically at `~/.config/sysmon/config.json`. Override via CLI flags.