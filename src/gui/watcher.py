"""File system watcher for GUI auto-reload functionality.

This module provides a watchdog event handler that triggers browser
reload events when source files change.
"""

import os
import time
from watchdog.events import FileSystemEventHandler


class ReloadEventHandler(FileSystemEventHandler):
    """Watchdog handler that broadcasts reload events on file changes.

    Debounces rapid sequences of file events to avoid spamming the browser.
    """

    def __init__(self, server, watch_exts: set[str], debounce_ms: int = 400):
        super().__init__()
        self.server = server
        self.watch_exts = {ext.lower() for ext in (watch_exts or {'.py'})}
        self.debounce_ms = debounce_ms
        self._last_emit = 0.0

    def _maybe_emit(self, path: str):
        try:
            ext = os.path.splitext(path)[1].lower()
            if self.watch_exts and ext not in self.watch_exts:
                return
        except Exception:
            pass
        now = time.time()
        if (now - self._last_emit) * 1000.0 >= self.debounce_ms:
            self._last_emit = now
            try:
                self.server.broadcast_reload()
            except Exception:
                pass

    # Handle any FS event uniformly
    def on_any_event(self, event):
        try:
            if getattr(event, 'is_directory', False):
                return
            self._maybe_emit(getattr(event, 'src_path', '') or '')
        except Exception:
            pass