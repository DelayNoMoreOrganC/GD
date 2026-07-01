"""In-process async task manager with progress tracking and WS broadcast."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("v5.task")


@dataclass
class ProgressTracker:
    task_id: int
    progress: float = 0.0
    stage: str = ""
    log_lines: list = field(default_factory=list)
    _subscribers: set = field(default_factory=set)

    def log(self, msg: str) -> None:
        if msg is None:
            return
        text = str(msg)
        self.log_lines.append(text)
        for q in list(self._subscribers):
            try:
                q.put_nowait({"type": "log", "text": text})
            except asyncio.QueueFull:
                pass

    def update(self, progress: float, stage: str = "") -> None:
        self.progress = progress
        if stage:
            self.stage = stage
        for q in list(self._subscribers):
            try:
                q.put_nowait({"type": "progress", "progress": self.progress, "stage": self.stage})
            except asyncio.QueueFull:
                pass

    def finish(self) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait({"type": "done"})
            except asyncio.QueueFull:
                pass

    def fail(self, error: str) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait({"type": "error", "error": error})
            except asyncio.QueueFull:
                pass

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)


class TaskManager:
    def __init__(self) -> None:
        self._trackers: dict = {}
        self._tasks: dict = {}
        self._sem = asyncio.Semaphore(1)

    def get_tracker(self, task_id: int) -> ProgressTracker:
        if task_id not in self._trackers:
            self._trackers[task_id] = ProgressTracker(task_id=task_id)
        return self._trackers[task_id]

    def start(self, task_id: int, coro) -> None:
        self._tasks[task_id] = asyncio.create_task(coro, name="archive-" + str(task_id))

    def is_running(self, task_id: int) -> bool:
        t = self._tasks.get(task_id)
        return t is not None and not t.done()

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._sem


task_manager = TaskManager()
