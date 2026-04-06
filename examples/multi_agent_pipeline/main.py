"""
Multi-Agent Pipeline — Supervisor + Workers + Dead Letter Queue
===============================================================
Demonstrates:
  - A supervisor that dispatches tasks to a pool of workers
  - Workers that fail occasionally (simulating real-world instability)
  - A Dead Letter Queue that captures exhausted tasks
  - A DLQ consumer that classifies and replays transient failures

Run:
    python3 examples/multi_agent_pipeline/main.py

No external dependencies required.
"""

import time
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class Task:
    id: str
    payload: str
    attempts: int = 0
    max_retries: int = 3
    error_type: Optional[str] = None   # set on failure


@dataclass
class DLQEntry:
    task: Task
    error: str
    error_class: str   # "transient" | "permanent" | "ambiguous"
    queued_at: float = field(default_factory=time.time)


# ── Worker agents ──────────────────────────────────────────────────────────────

class WorkerAgent:
    """Narrow specialist — processes one task type. Fails stochastically."""

    def __init__(self, name: str, fail_rate: float = 0.3):
        self.name = name
        self.fail_rate = fail_rate

    def run(self, task: Task) -> str:
        task.attempts += 1
        if random.random() < self.fail_rate:
            # Alternate between failure types to demo classification
            err_type = "ConnectionError" if task.attempts % 2 == 0 else "ValueError"
            task.error_type = err_type
            raise RuntimeError(f"[{self.name}] failed on '{task.id}': {err_type}")
        return f"[{self.name}] processed '{task.id}' in {task.attempts} attempt(s)"


# ── Dead Letter Queue ──────────────────────────────────────────────────────────

class DeadLetterQueue:
    """In-memory DLQ. Production equivalent: Redis list or Postgres table."""

    def __init__(self):
        self._queue: deque[DLQEntry] = deque()

    def push(self, task: Task, error: str):
        entry = DLQEntry(
            task=task,
            error=error,
            error_class=self._classify(task),
        )
        self._queue.append(entry)
        print(f"  [DLQ] queued '{task.id}' — class={entry.error_class}, attempts={task.attempts}")

    def drain(self) -> list[DLQEntry]:
        entries, self._queue = list(self._queue), deque()
        return entries

    def __len__(self):
        return len(self._queue)

    @staticmethod
    def _classify(task: Task) -> str:
        """
        Classify failure type to decide replay strategy.
        Production logic would inspect error codes, not just type strings.
        """
        if task.error_type == "ConnectionError":
            return "transient"     # safe to replay after backoff
        if task.error_type == "ValueError":
            return "permanent"     # bad input — needs human review
        return "ambiguous"         # LLM-level — try once with different params


# ── Supervisor ─────────────────────────────────────────────────────────────────

class Supervisor:
    """
    Control plane. Decomposes work → dispatches to workers → handles failures.
    Sends exhausted tasks to the DLQ instead of crashing.
    """

    def __init__(self, workers: list[WorkerAgent], dlq: DeadLetterQueue):
        self.workers = workers
        self.dlq = dlq
        self._worker_idx = 0   # round-robin dispatch

    def dispatch(self, task: Task) -> Optional[str]:
        """Try to run the task, retrying up to max_retries. Returns result or None."""
        worker = self._pick_worker()
        while task.attempts < task.max_retries:
            try:
                result = worker.run(task)
                return result
            except RuntimeError as e:
                print(f"  [supervisor] worker error: {e} — retrying ({task.attempts}/{task.max_retries})")
                time.sleep(0.05 * task.attempts)  # simple backoff

        # Exhausted — send to DLQ
        self.dlq.push(task, error=f"Exceeded {task.max_retries} retries")
        return None

    def _pick_worker(self) -> WorkerAgent:
        # Round-robin across the worker pool
        w = self.workers[self._worker_idx % len(self.workers)]
        self._worker_idx += 1
        return w


# ── DLQ Consumer ──────────────────────────────────────────────────────────────

def replay_dlq(dlq: DeadLetterQueue, workers: list[WorkerAgent]):
    """
    Out-of-band process: drain DLQ, classify, and replay transient failures.
    Permanent failures are logged for human review.
    """
    entries = dlq.drain()
    if not entries:
        print("  [DLQ consumer] nothing to replay")
        return

    print(f"\n  [DLQ consumer] processing {len(entries)} entries...")
    for entry in entries:
        if entry.error_class == "transient":
            # Reset attempts and replay with a healthy worker
            entry.task.attempts = 0
            entry.task.error_type = None
            worker = workers[0]   # pick first (assumed healthy after delay)
            try:
                result = worker.run(entry.task)
                print(f"  [DLQ consumer] replayed OK: {result}")
            except Exception as e:
                print(f"  [DLQ consumer] replay failed again: {e} — escalating to human")
        elif entry.error_class == "permanent":
            print(f"  [DLQ consumer] '{entry.task.id}' needs human review: {entry.error}")
        else:
            print(f"  [DLQ consumer] ambiguous '{entry.task.id}' — flagged for re-prompt")


# ── Demo harness ───────────────────────────────────────────────────────────────

def demo():
    random.seed(7)

    tasks = [Task(id=f"task-{i}", payload=f"data-{i}") for i in range(10)]
    workers = [
        WorkerAgent("nlp-worker",  fail_rate=0.4),
        WorkerAgent("code-worker", fail_rate=0.3),
    ]
    dlq = DeadLetterQueue()
    supervisor = Supervisor(workers=workers, dlq=dlq)

    print("=" * 60)
    print("Phase 1: Supervisor dispatching 10 tasks")
    print("=" * 60)
    results = []
    for task in tasks:
        result = supervisor.dispatch(task)
        if result:
            print(f"  OK: {result}")
            results.append(result)
        else:
            print(f"  FAILED: '{task.id}' moved to DLQ")

    print(f"\nCompleted: {len(results)}/10  |  DLQ depth: {len(dlq)}")

    print()
    print("=" * 60)
    print("Phase 2: DLQ consumer replays transient failures")
    print("=" * 60)
    # Simulate recovery — drop fail rate before replay
    for w in workers:
        w.fail_rate = 0.0
    replay_dlq(dlq, workers)

    print()
    print("Done. Permanent failures were isolated; transient failures replayed.")


if __name__ == "__main__":
    demo()
