"""Base HTTP request handler for the GUI web interface.

This module provides the base request handler class with utility methods
for handling HTTP requests, JSON responses, and upstream proxying.
"""

import json
import logging
import sys
import time
import urllib.request
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GUIRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the GUI web app and JSON APIs.

    Serves the single-page UI, SSE reload stream, and JSON endpoints
    for plugins, learning insights, message processing, delegation, and tools.
    """
    
    # Will be set by GUIInterface during initialization
    INDEX_HTML = None

    def log_message(self, format: str, *args) -> None:  # reduce console noise
        logger.debug("GUI HTTP: " + format, *args)

    # --- NEW: Suppress benign client disconnect errors at server level ---
    def handle_error(self, request, client_address):
        try:
            exc_type, exc_value, _ = sys.exc_info()
            if exc_type in (ConnectionAbortedError, BrokenPipeError):
                try:
                    logger.debug("GUI HTTP: suppressed client disconnect from %s: %s", client_address, exc_value)
                except Exception:
                    pass
                return
        except Exception:
            pass
        # Fallback to default behavior
        try:
            return super().handle_error(request, client_address)
        except Exception:
            pass

    def _json(self, status: int, data: Dict[str, Any]):
        """Send JSON response with error handling for client disconnects."""
        try:
            body = json.dumps(data).encode("utf-8")
        except Exception:
            try:
                body = json.dumps({"error": "serialization_failure", "repr": str(data)}).encode("utf-8")
            except Exception:
                body = b"{}"
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionAbortedError, BrokenPipeError):
                return
            except Exception:
                return
        except (ConnectionAbortedError, BrokenPipeError):
            return
        except Exception:
            return

    @contextmanager
    def _fetch_with_backoff(self, req, timeout: float = 5.0, attempts: int = 4, base_delay: float = 0.25, max_delay: float = 2.0):
        """
        Attempt to open the given urllib.request.Request with exponential backoff.
        - Retries only on transient network errors (URLError, timeouts, ConnectionReset)
        - Does NOT retry on upstream HTTP errors (HTTPError); those are raised for caller to forward
        - Yields a response object that is closed automatically on context exit
        """
        last_exc = None
        for i in range(int(max(1, attempts))):
            try:
                r = urllib.request.urlopen(req, timeout=timeout)
                try:
                    yield r
                finally:
                    try:
                        r.close()
                    except Exception:
                        pass
                return
            except urllib.error.HTTPError as e:
                # Do not retry on HTTP error; forward upstream status as-is
                raise
            except Exception as e:
                # Transient error: backoff and retry
                last_exc = e
                if i + 1 >= int(max(1, attempts)):
                    break
                try:
                    # Progressive delay: base * 2^i, capped to max_delay
                    delay = base_delay * (2 ** i)
                    if max_delay is not None:
                        delay = min(delay, max_delay)
                    time.sleep(delay)
                except Exception:
                    pass
        # Exhausted retries; raise last exception for caller
        if last_exc is not None:
            raise last_exc
        # Fallback: raise a generic error
        raise RuntimeError("Upstream fetch failed without specific exception")

    # Import route handlers
    from .get_routes import do_GET
    from .post_routes import do_POST