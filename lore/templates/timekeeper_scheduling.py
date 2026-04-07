# LORE SCAFFOLD: timekeeper_scheduling
"""
Timekeeper Scheduling — The Timekeeper, Scheduler of All Things Async

KAIROS loop pattern: check → act → rest. The Timekeeper governs what happens
when you are not watching. Configurable intervals, heartbeat tracking, and
graceful shutdown.

Usage:
    loop = KairosLoop(name="research-scout", interval_seconds=1800)
    loop.register_action(my_research_fn)
    await loop.run()  # Runs until stopped
    # Or: loop.stop()
"""

from __future__ import annotations

import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HeartbeatRecord:
    """Tracks loop health."""
    iteration: int = 0
    last_check: float = 0.0
    last_action: float = 0.0
    last_error: str = ""
    consecutive_errors: int = 0
    total_actions: int = 0
    total_errors: int = 0


class KairosLoop:
    """KAIROS loop: check condition → act → rest → repeat.

    Supports async and sync action functions, graceful shutdown via
    stop() or SIGTERM/SIGINT, and heartbeat monitoring.
    """

    def __init__(
        self,
        name: str = "kairos",
        interval_seconds: float = 60.0,
        max_consecutive_errors: int = 5,
        error_backoff_multiplier: float = 2.0,
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.max_consecutive_errors = max_consecutive_errors
        self.error_backoff_multiplier = error_backoff_multiplier
        self._actions: list[Callable] = []
        self._running = False
        self.heartbeat = HeartbeatRecord()

    def register_action(self, fn: Callable) -> None:
        """Register an action to run each cycle."""
        self._actions = [*self._actions, fn]

    def stop(self) -> None:
        """Signal the loop to stop after current cycle."""
        self._running = False

    async def run(self) -> None:
        """Run the KAIROS loop: check → act → rest."""
        self._running = True

        # Handle graceful shutdown signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler

        while self._running:
            self.heartbeat.iteration += 1
            self.heartbeat.last_check = time.time()

            # Act: run all registered actions
            for action in self._actions:
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()
                    self.heartbeat.last_action = time.time()
                    self.heartbeat.total_actions += 1
                    self.heartbeat.consecutive_errors = 0
                except Exception as e:
                    self.heartbeat.last_error = str(e)
                    self.heartbeat.consecutive_errors += 1
                    self.heartbeat.total_errors += 1

                    if self.heartbeat.consecutive_errors >= self.max_consecutive_errors:
                        self._running = False
                        break

            # Rest: sleep with backoff on errors
            sleep_time = self.interval_seconds
            if self.heartbeat.consecutive_errors > 0:
                sleep_time *= self.error_backoff_multiplier ** self.heartbeat.consecutive_errors

            if self._running:
                await asyncio.sleep(sleep_time)

    def status(self) -> dict:
        """Return current loop status."""
        return {
            "name": self.name,
            "running": self._running,
            "iteration": self.heartbeat.iteration,
            "total_actions": self.heartbeat.total_actions,
            "total_errors": self.heartbeat.total_errors,
            "consecutive_errors": self.heartbeat.consecutive_errors,
            "last_error": self.heartbeat.last_error,
            "uptime_seconds": time.time() - self.heartbeat.last_check if self.heartbeat.last_check else 0,
        }
