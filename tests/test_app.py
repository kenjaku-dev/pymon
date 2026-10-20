"""Smoke tests for the TUI app."""

from __future__ import annotations

import asyncio

from pymon.app import PymonApp
from pymon.config import Config


def test_app_runs() -> None:
    async def main() -> None:
        app = PymonApp(config=Config())
        async with app.run_test() as pilot:
            await pilot.pause(1.5)
            assert app.snapshot is not None
            assert app.snapshot.processes

    asyncio.run(main())


def test_help_opens() -> None:
    async def main() -> None:
        app = PymonApp(config=Config())
        async with app.run_test() as pilot:
            await pilot.pause(0.5)
            await pilot.press("h")
            await pilot.pause(0.3)
            assert len(app.screen_stack) == 2
            await pilot.press("escape")
            await pilot.pause(0.3)
            assert len(app.screen_stack) == 1

    asyncio.run(main())
