"""
MCP Event Storage - In-memory event storage for MCP tool sessions
"""
import time
import threading
from collections import deque
from typing import Dict, List, Any, Optional
from datetime import datetime


class MCPEventStorage:
    """Thread-safe in-memory storage for MCP tool events per session"""

    def __init__(self, max_events_per_session: int = 1000):
        self.max_events = max_events_per_session
        self._events: Dict[str, deque] = {}  # session_id -> deque of events
        self._metrics: Dict[str, Dict[str, Any]] = {}  # session_id -> metrics
        self._lock = threading.Lock()

    def add_event(self, session_id: str, event_type: str, payload: Any, timestamp: Optional[float] = None):
        """
        Add an event to a session's event log.

        Args:
            session_id: Session identifier
            event_type: Event type (e.g., 'tool_call', 'result', 'error', 'log')
            payload: Event payload data
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        event = {
            'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
            'type': event_type,
            'payload': payload
        }

        with self._lock:
            # Initialize session storage if needed
            if session_id not in self._events:
                self._events[session_id] = deque(maxlen=self.max_events)
                self._metrics[session_id] = {
                    'operations_count': 0,
                    'error_count': 0,
                    'total_response_time': 0.0,
                    'response_count': 0,
                    'last_activity': timestamp
                }

            # Add event
            self._events[session_id].append(event)

            # Update metrics
            metrics = self._metrics[session_id]
            metrics['last_activity'] = timestamp

            if event_type in ['tool_call', 'result', 'success']:
                metrics['operations_count'] += 1

            if event_type == 'error':
                metrics['error_count'] += 1

            # Track response times if payload has timing info
            if isinstance(payload, dict) and 'response_time_ms' in payload:
                metrics['total_response_time'] += payload['response_time_ms']
                metrics['response_count'] += 1

    def get_events(self, session_id: str, since: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get events for a session, optionally filtered by index.

        Args:
            session_id: Session identifier
            since: Optional index to get events after

        Returns:
            List of events
        """
        with self._lock:
            if session_id not in self._events:
                return []

            events = list(self._events[session_id])

            if since is not None and since >= 0:
                # Return events after the 'since' index
                return events[since:]

            return events

    def get_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get metrics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Metrics dictionary
        """
        with self._lock:
            if session_id not in self._metrics:
                return {
                    'operations_count': 0,
                    'error_count': 0,
                    'avg_response_time_ms': 0,
                    'last_activity': None
                }

            metrics = self._metrics[session_id].copy()

            # Calculate average response time
            if metrics['response_count'] > 0:
                metrics['avg_response_time_ms'] = int(
                    metrics['total_response_time'] / metrics['response_count']
                )
            else:
                metrics['avg_response_time_ms'] = 0

            # Format last activity
            if metrics['last_activity']:
                metrics['last_activity'] = datetime.fromtimestamp(
                    metrics['last_activity']
                ).strftime('%H:%M:%S')
            else:
                metrics['last_activity'] = 'Never'

            # Clean up internal fields
            metrics.pop('total_response_time', None)
            metrics.pop('response_count', None)

            return metrics

    def clear_session(self, session_id: str):
        """Clear all events and metrics for a session"""
        with self._lock:
            self._events.pop(session_id, None)
            self._metrics.pop(session_id, None)

    def get_all_sessions(self) -> List[str]:
        """Get list of all session IDs with stored events"""
        with self._lock:
            return list(self._events.keys())


# Global event storage instance
_event_storage = MCPEventStorage()


def get_event_storage() -> MCPEventStorage:
    """Get the global event storage instance"""
    return _event_storage
