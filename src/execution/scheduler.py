"""Background Scheduler service for MCP jobs.

Consumes TaskQueue, emits SSE report events to the GUI, and performs
lightweight routing based on the job's server_target. Phase 1 stub keeps
processing simple and observable via SSE.

Follows project code conventions: clear docstrings, logging, and
thread-safe operations where relevant.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Any, Optional

from src.core.task_queue import TaskQueue
from src.core.mcp_contracts import ReportEvent, MCPJobSpec

logger = logging.getLogger(__name__)


class Scheduler:
    """Simple background scheduler for MCP jobs.

    - Polls a TaskQueue for jobs
    - Emits SSE 'mcp.job.report' events for lifecycle states
    - Performs minimal routing for known server targets (e.g. 'playwright')

    Args:
        queue: TaskQueue instance to consume jobs from
        emit: Callable taking (channel: str, data: Dict[str, Any]) to broadcast SSE
        interval_seconds: Polling interval when queue is empty
    """

    def __init__(self, *, queue: TaskQueue, emit: Callable[[str, Dict[str, Any]], None], interval_seconds: float = 0.5) -> None:
        self._queue = queue
        self._emit = emit
        self._interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the scheduler loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="MCPScheduler", daemon=True)
        self._thread.start()
        logger.info("MCP Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler loop and join the thread."""
        if not self._running:
            return
        self._running = False
        try:
            if self._thread:
                self._thread.join(timeout=2.0)
        except Exception:
            # Avoid noisy logs on shutdown races
            pass
        finally:
            self._thread = None
        logger.info("MCP Scheduler stopped")

    # ------------------------------ Internal ------------------------------
    def _run_loop(self) -> None:
        """Main scheduler loop: poll queue and process jobs."""
        while self._running:
            try:
                job = self._queue.poll()
                if job is None:
                    # No work; sleep briefly
                    time.sleep(self._interval)
                    continue
                self._process_job(job)
            except Exception as e:
                # Log and continue; scheduler should be resilient
                logger.debug(f"Scheduler loop error: {e}")
                time.sleep(self._interval)

    def _process_job(self, job: MCPJobSpec) -> None:
        """Process a single job and emit report events."""
        # Emit RUNNING state
        try:
            self._emit('mcp.job.report', ReportEvent(
                correlation_id=job.correlation_id,
                job_id=job.job_id,
                state='running',
                message=f"Job started on target '{job.server_target}'",
            ).to_dict())
        except Exception:
            # Non-fatal if emit fails; continue processing
            pass

        try:
            # Minimal routing by server_target
            target = (job.server_target or '').strip().lower()

            if target == 'playwright':
                # Signal UI to open the Playwright tab/pane (existing SSE handler)
                try:
                    self._emit('open_playwright', {
                        'correlation_id': job.correlation_id,
                        'job_id': job.job_id,
                        'task': job.task,
                        'info': 'Scheduler requested Playwright UI'
                    })
                except Exception:
                    pass
                # Simulate brief work for Phase 1
                time.sleep(0.2)
                outputs: Dict[str, Any] = {
                    'route': 'playwright',
                    'note': 'Routed to Playwright server (stub)'
                }
            else:
                # Unknown target: simulate processing
                time.sleep(0.2)
                outputs = {
                    'route': 'noop',
                    'note': f"No executor for target '{target}' (stub)"
                }

            # Emit COMPLETED state
            try:
                self._emit('mcp.job.report', ReportEvent(
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                    state='completed',
                    message='Job completed',
                    outputs=outputs
                ).to_dict())
            except Exception:
                pass
        except Exception as e:
            # Emit ERROR state if processing failed
            try:
                self._emit('mcp.job.report', ReportEvent(
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                    state='error',
                    message=f"Job failed: {e}"
                ).to_dict())
            except Exception:
                pass
            logger.debug(f"Job processing error: {e}")