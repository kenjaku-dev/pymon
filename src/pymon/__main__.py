"""Entry point for the pymon CLI."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pymon.app import PymonApp
from pymon.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pymon", description="Linux system monitor TUI")
    parser.add_argument("--config", type=Path, default=None, help="path to config JSON")
    parser.add_argument("--refresh", type=float, default=None, help="refresh interval seconds")
    parser.add_argument("--theme", choices=["dark", "light"], default=None, help="color theme")
    parser.add_argument(
        "--sort", choices=["cpu", "mem", "pid", "name"], default=None, help="process sort column"
    )
    parser.add_argument("--desc", action="store_true", default=None, help="sort descending")
    parser.add_argument("--asc", action="store_true", default=None, help="sort ascending")
    parser.add_argument("--rows", type=int, default=None, help="max process rows")
    parser.add_argument("--version", action="version", version="pymon 0.1.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log_dir = Path.home() / ".local" / "share" / "pymon"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "pymon.log"),
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    if args.refresh is not None:
        config.refresh_interval = max(0.1, min(10.0, args.refresh))
    if args.theme is not None:
        config.theme = args.theme
    if args.sort is not None:
        config.process_sort = args.sort
    if args.desc:
        config.process_sort_desc = True
    if args.asc:
        config.process_sort_desc = False
    if args.rows is not None:
        config.process_row_cap = max(1, args.rows)
    app = PymonApp(config=config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())