"""MCP contracts and event schemas.

Defines structured types and helpers for scheduling MCP jobs and reporting
progress back to the GUI via SSE. Keep minimal and JSON-friendly.

This module follows the project's existing code style: clear docstrings,
logging where appropriate, and simple, explicit data structures.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def _now_iso() -> str:
    """Return current UTC time in ISO-8601 (with Z)."""
    return datetime.utcnow().strftime(ISO)


def make_job_id() -> str:
    """Generate a short job ID."""
    return uuid.uuid4().hex[:12]


def make_correlation_id() -> str:
    """Generate a correlation ID to link job and its event stream."""
    return uuid.uuid4().hex


@dataclass
class MCPJobSpec:
    """Specification of a scheduled MCP job.

    Attributes:
        job_id: Unique ID for this job (short hex).
        correlation_id: Unique ID to correlate SSE events and reports.
        server_target: MCP server name/identifier (e.g. "playwright").
        task: Natural language task description.
        params: Optional parameters for the job.
        created_at: ISO timestamp when the job was created.
    """
    job_id: str
    correlation_id: str
    server_target: str
    task: str
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReportEvent:
    """Incoming report from a running MCP job.

    Attributes:
        correlation_id: ID to correlate with the job.
        job_id: Job ID.
        state: One of {queued, running, completed, error, canceled}.
        message: Optional human-readable status message.
        outputs: Optional structured outputs.
        artifacts: Optional list of artifacts (e.g. files, images, urls).
        timestamp: ISO timestamp of the event.
    """
    correlation_id: str
    job_id: str
    state: str
    message: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[Dict[str, Any]]] = None
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobEnqueuedEvent:
    """Outgoing event to notify GUI that a job has been enqueued."""
    correlation_id: str
    job_id: str
    server_target: str
    task: str
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)