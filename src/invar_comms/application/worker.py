"""Minimal outbox worker: pull one durable job, run its handler, record result.

Deliberately boring (no broker, no threads, no scheduler): the webhook
endpoint (roadmap task 3) will enqueue jobs and call `process_next` from a
simple loop/cron. Handlers are plain callables; unknown job types fail
permanently instead of being silently dropped or retried forever. Retries are
immediate (bounded by max_attempts); time-based backoff is deferred until a
real delivery-failure profile exists to tune it against.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..ports.repositories import Outbox

JobHandler = Callable[[dict[str, Any]], None]


class OutboxWorker:
    def __init__(
        self,
        outbox: Outbox,
        handlers: dict[str, JobHandler],
        *,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._outbox = outbox
        self._handlers = dict(handlers)
        self._max_attempts = max_attempts

    def process_next(self) -> bool:
        """Process a single pending job. Returns False when the queue is empty."""
        jobs = self._outbox.fetch_pending(limit=1)
        if not jobs:
            return False
        job = jobs[0]
        handler = self._handlers.get(job.job_type)
        if handler is None:
            self._outbox.mark_failed(
                job.job_id, f"no handler for job_type={job.job_type!r}", retry=False
            )
            return True
        try:
            handler(job.payload)
        except Exception as exc:  # noqa: BLE001 - job boundary: record, don't crash
            retry = job.attempts + 1 < self._max_attempts
            self._outbox.mark_failed(job.job_id, f"{type(exc).__name__}: {exc}",
                                     retry=retry)
            return True
        self._outbox.mark_done(job.job_id)
        return True

    def drain(self, *, max_jobs: int = 100) -> int:
        """Process up to `max_jobs`; returns how many jobs were attempted."""
        processed = 0
        while processed < max_jobs and self.process_next():
            processed += 1
        return processed
