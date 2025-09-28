"""Simple FIFO TaskQueue for MCP jobs.

Thread-safe queue that assigns job IDs and correlation IDs if missing, and
exposes non-blocking poll for the Scheduler. Designed to integrate with the
GUI HTTP server and the Scheduler service.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Optional, Deque

from .mcp_contracts import MCPJobSpec, make_job_id, make_correlation_id


class TaskQueue:
    """Thread-safe FIFO queue of MCPJobSpec.

    - put(job): enqueue job
    - poll(): non-blocking pop-left or None
    - size: number of queued jobs
    """

    def __init__(self) -> None:
        self._dq: Deque[MCPJobSpec] = deque()
        self._lock = threading.Lock()

    def put(self, job: MCPJobSpec) -> MCPJobSpec:
        """Enqueue a job. Ensure job_id and correlation_id are set."""
        with self._lock:
            if not job.job_id:
                job.job_id = make_job_id()
            if not job.correlation_id:
                job.correlation_id = make_correlation_id()
            self._dq.append(job)
            return job

    def poll(self) -> Optional[MCPJobSpec]:
        """Pop one job if available, else None. Non-blocking."""
        with self._lock:
            if self._dq:
                return self._dq.popleft()
            return None

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._dq)