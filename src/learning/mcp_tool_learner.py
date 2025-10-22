from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..memory import MemoryManager, Memory, MemoryType


@dataclass
class ToolUsageEvent:
    tool: str
    args: Any
    success: bool
    duration_ms: int
    context: Dict[str, Any]
    timestamp: str


class MCPToolLearner:
    """Learns when and how to use MCP tools based on telemetry.

    - Records structured tool usage events into memory (procedural/long-term)
    - Aggregates assistant.metrics['tool_metrics'] for success-rate and latency
    - Suggests tools for a given task context using simple heuristics
    - Provides feature vectors for reinforcement/evolutionary learners if needed
    """

    def __init__(self, assistant: Any) -> None:
        self.assistant = assistant
        # Cache pointer to memory manager for convenience
        self.memory_manager: Optional[MemoryManager] = getattr(assistant, "memory_manager", None)

    async def record_event(
        self,
        tool: str,
        args: Any,
        success: bool,
        duration_ms: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a tool usage event into memory and update metrics bucket if present."""
        ts = datetime.now().isoformat()
        ev = ToolUsageEvent(
            tool=tool,
            args=args,
            success=success,
            duration_ms=max(0, int(duration_ms or 0)),
            context=context or {},
            timestamp=ts,
        )

        # Store as procedural memory for future retrieval and pattern detection
        try:
            if self.memory_manager is not None:
                mem = Memory(
                    type=MemoryType.PROCEDURAL,
                    content=json.dumps({
                        "tool": ev.tool,
                        "args": ev.args,
                        "success": ev.success,
                        "duration_ms": ev.duration_ms,
                        "timestamp": ev.timestamp,
                    }),
                    context={
                        "kind": "mcp_tool_usage",
                        "source": "plugin",
                        **(ev.context or {}),
                    },
                    importance=0.3,
                )
                await self.memory_manager.store_memory(mem)
                # Also register pattern for aggregation by PatternDetector
                await self.memory_manager.detect_pattern("tool_usage", {
                    "tool": ev.tool,
                    "args": ev.args,
                    "success": ev.success,
                    "duration_ms": ev.duration_ms,
                    "timestamp": ev.timestamp,
                    "source": "plugin",
                })
        except Exception:
            # Non-critical; proceed silently
            pass

        # Update metrics bucket if available (keeps UI in sync)
        try:
            bucket = self.assistant.metrics.get("tool_metrics", {})
            tools = bucket.setdefault("tools", {})
            rec = tools.setdefault(tool, {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_latency_ms": 0,
            })
            rec["calls"] += 1
            if success:
                rec["successes"] += 1
            else:
                rec["failures"] += 1
            rec["total_latency_ms"] += ev.duration_ms
            bucket["last_updated"] = ts
            self.assistant.metrics["tool_metrics"] = bucket
        except Exception:
            pass

    def suggest_tools(self, task_hint: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Suggest tools based on success rate and average latency.

        Simple scoring: score = success_rate * 100 - avg_latency_ms * 0.01,
        with lightweight filtering based on task_hint keywords.
        """
        try:
            metrics = self.assistant.metrics.get("tool_metrics", {})
            tools = metrics.get("tools", {})
            scored: List[Tuple[str, float, int, int]] = []
            for name, rec in tools.items():
                calls = int(rec.get("calls", 0) or 0)
                succ = int(rec.get("successes", 0) or 0)
                total_lat = int(rec.get("total_latency_ms", 0) or 0)
                if calls <= 0:
                    continue
                success_rate = succ / calls if calls > 0 else 0.0
                avg_latency_ms = int(total_lat / calls) if calls > 0 else 0
                # Basic keyword affinity
                hint = (task_hint or "").lower()
                if hint:
                    if ".search" in name and ("search" in hint or "find" in hint):
                        pass
                    elif "desktop" in name and ("open" in hint or "run" in hint or "execute" in hint):
                        pass
                    elif "ctx7" in name and ("docs" in hint or "library" in hint or "context" in hint):
                        pass
                    # Penalize if no obvious match
                    else:
                        success_rate *= 0.9
                score = success_rate * 100.0 - avg_latency_ms * 0.01
                scored.append((name, score, avg_latency_ms, int(success_rate * 100)))

            scored.sort(key=lambda x: x[1], reverse=True)
            out: List[Dict[str, Any]] = []
            for name, score, avg_lat, succ_pct in scored[:max(1, top_k)]:
                out.append({
                    "name": name,
                    "score": round(score, 2),
                    "avg_latency_ms": avg_lat,
                    "success_rate_pct": succ_pct,
                })
            return out
        except Exception:
            return []

    def features_for_rl(self) -> Dict[str, Any]:
        """Provide a compact feature summary for RL state augmentation."""
        try:
            metrics = self.assistant.metrics.get("tool_metrics", {})
            tools = metrics.get("tools", {})
            # Top-3 by calls
            top = sorted([
                (name, rec.get("calls", 0) or 0)
                for name, rec in tools.items()
            ], key=lambda x: x[1], reverse=True)[:3]
            return {
                "tool_top_calls": [t[0] for t in top],
                "tool_top_calls_count": [t[1] for t in top],
                "tools_total": len(tools),
            }
        except Exception:
            return {"tools_total": 0}