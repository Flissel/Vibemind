"""Main GUI interface for the Sakana Desktop Assistant.

This module provides the GUIInterface class which manages the entire
web-based GUI system including HTTP server, event loops, and file watching.
"""

import asyncio
import logging
import os
import threading
from pathlib import Path
from watchdog.observers import Observer

from .server import AssistantHTTPServer
from .handlers import GUIRequestHandler
from .watcher import ReloadEventHandler

logger = logging.getLogger(__name__)


class GUIInterface:
    """Graphical (web) interface that serves the minimal SPA and JSON APIs.

    Follows the same interface contract as CLIInterface with
    async initialize(), run(), and shutdown() methods.
    """

    def __init__(self, assistant, host: str = "127.0.0.1", port: int = 8765):
        # Keep references for request handlers and for main to log host/port
        self.assistant = assistant
        self.host = host
        self.port = port
        
        # HTTP server and threads
        self._httpd = None
        self._server_thread = None
        
        # Dedicated asyncio loop running in a background thread for async tasks
        self.loop = None
        self._loop_thread = None
        
        # Filesystem watcher for UI auto-reload
        self._observer = None

        # Control flag for run loop
        self._running = False
        
        # --- React UI serving configuration (for migration) ---
        try:
            cfg = getattr(self.assistant, 'config', None)
            print(f"DEBUG: Assistant config object: {cfg}")
            print(f"DEBUG: Config type: {type(cfg)}")
            if cfg:
                print(f"DEBUG: Config attributes: {dir(cfg)}")
                raw_enabled = getattr(cfg, 'react_ui_enabled', False)
                print(f"DEBUG: Raw react_ui_enabled value: {raw_enabled}, type: {type(raw_enabled)}")
            self._react_ui_enabled = bool(getattr(cfg, 'react_ui_enabled', False))
            dist_dir = getattr(cfg, 'react_ui_dist_dir', None)
            print(f"DEBUG: React UI config - enabled: {self._react_ui_enabled}, dist_dir: {dist_dir}")
            if dist_dir:
                try:
                    self._react_ui_dist_dir = Path(dist_dir)
                except Exception:
                    self._react_ui_dist_dir = None
            else:
                try:
                    self._react_ui_dist_dir = Path(__file__).resolve().parents[1] / 'ui' / 'webapp' / 'dist'
                except Exception:
                    self._react_ui_dist_dir = None
            print(f"DEBUG: React UI dist_dir resolved to: {self._react_ui_dist_dir}")
        except Exception as e:
            print(f"DEBUG: React UI config access failed: {e}")
            self._react_ui_enabled = False
            self._react_ui_dist_dir = None
        
        # Disable React UI if dist directory doesn't exist
        if self._react_ui_dist_dir and not self._react_ui_dist_dir.exists():
            print(f"DEBUG: React UI disabled - dist directory doesn't exist: {self._react_ui_dist_dir}")
            self._react_ui_enabled = False
        
        print(f"DEBUG: Final React UI state - enabled: {self._react_ui_enabled}, dist_dir: {self._react_ui_dist_dir}")
        
        # --- TaskQueue and Scheduler references ---
        self._task_queue = None
        self._scheduler = None

    async def initialize(self):
        """Initialize web server and background event loop."""
        # Start dedicated asyncio loop in a background thread
        loop_ready = threading.Event()

        def _loop_worker():
            # Create and run a dedicated event loop for GUI async tasks
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self.loop = new_loop
            loop_ready.set()
            try:
                new_loop.run_forever()
            finally:
                try:
                    new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                except Exception:
                    pass
                new_loop.close()

        self._loop_thread = threading.Thread(target=_loop_worker, name="GUIAsyncLoop", daemon=True)
        self._loop_thread.start()
        # Wait until loop is ready before starting HTTP server
        loop_ready.wait(timeout=5)

        # Build inline HTML for the GUI and assign to handler class
        try:
            GUIRequestHandler.INDEX_HTML = self._build_index_html()
        except Exception:
            logger.exception("Failed to build INDEX_HTML; using minimal fallback UI")
            GUIRequestHandler.INDEX_HTML = "<html><body><h1>GUI</h1><p>Initialization fallback.</p></body></html>"

        # Bind HTTP server; if port is busy, try a few subsequent ports
        bind_host = self.host
        bind_port = self.port
        last_err = None
        for attempt in range(0, 10):
            try:
                self._httpd = AssistantHTTPServer((bind_host, bind_port), GUIRequestHandler, self.assistant, self.loop, self._react_ui_enabled, self._react_ui_dist_dir)
                break
            except OSError as e:
                last_err = e
                bind_port += 1
        if self._httpd is None:
            raise RuntimeError(f"Failed to start GUI server: {last_err}")

        # Update actual bound address for logging in main
        self.host, self.port = self._httpd.server_address

        # --- Attach Orchestrator, TaskQueue, and start Scheduler ---
        try:
            from ..core.orchestrator import Orchestrator
            if not hasattr(self.assistant, 'orchestrator') or getattr(self.assistant, 'orchestrator') is None:
                setattr(self.assistant, 'orchestrator', Orchestrator())
        except Exception:
            logger.debug("Failed to attach Orchestrator; proceeding without it")
        
        try:
            from ..core.task_queue import TaskQueue
            self._task_queue = TaskQueue()
            setattr(self._httpd, 'task_queue', self._task_queue)
            
            from ..execution.scheduler import Scheduler
            self._scheduler = Scheduler(queue=self._task_queue, emit=self._httpd.broadcast_event)
            self._scheduler.start()
            logger.info("Scheduler started for MCP jobs")
        except Exception as e:
            logger.debug(f"Scheduler setup failed: {e}")

        # Start HTTP server in its own thread
        def _serve():
            try:
                self._httpd.serve_forever(poll_interval=0.5)
            except Exception:
                pass

        self._server_thread = threading.Thread(target=_serve, name="GUIHTTPServer", daemon=True)
        self._server_thread.start()
        self._running = True

        # Start file watcher to broadcast reload events on code changes
        try:
            exts = {'.py', '.js', '.css', '.html', '.json'}
            handler = ReloadEventHandler(self._httpd, watch_exts=exts, debounce_ms=500)
            observer = Observer()
            watch_dirs = []
            try:
                cfg = getattr(self.assistant, 'config', None)
                if cfg:
                    watch_dirs.append(str(cfg.base_dir / 'src'))
                    watch_dirs.append(str(cfg.plugins_dir))
            except Exception:
                pass
            ui_dir = os.path.dirname(__file__)
            if ui_dir:
                watch_dirs.append(ui_dir)
            for d in watch_dirs:
                if d and os.path.isdir(d):
                    observer.schedule(handler, d, recursive=True)
            observer.daemon = True
            observer.start()
            self._observer = observer
            logger.info(f"Auto-reload watcher started for: {', '.join([d for d in watch_dirs if os.path.isdir(d)])}")
        except Exception as e:
            logger.debug(f"Auto-reload watcher not started: {e}")

        logger.info(f"GUI server started at http://{self.host}:{self.port}/")

    async def run(self):
        """Keep GUI server running asynchronously."""
        while self._running:
            await asyncio.sleep(1)

    async def shutdown(self):
        """Shutdown GUI server, file watcher, and background event loop."""
        # Stop HTTP server
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass
        finally:
            self._httpd = None
        
        # Stop Scheduler
        try:
            if self._scheduler:
                self._scheduler.stop()
        except Exception:
            pass
        finally:
            self._scheduler = None
            self._task_queue = None

    def _build_index_html(self) -> str:
        """Construct inline HTML for the GUI.
        
        Includes:
        - Minimal chat input and output area
        - SSE connection to /events for hot-reload
        - Buttons to list plugins and send messages
        """
        from string import Template
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Sakana Desktop Assistant</title>
<style>
  body { font-family: system-ui, Arial, sans-serif; margin: 0; background: #0b1f2a; color: #e6f1ff; }
  header { padding: 16px 20px; background: #0f2b3a; border-bottom: 1px solid #163a4d; }
  h1 { margin: 0; font-size: 18px; }
  main { padding: 16px 20px; }
  .row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
  input[type=text] { flex: 1; min-width: 240px; padding: 10px; border-radius: 6px; border: 1px solid #28536b; background: #0c2230; color: #e6f1ff; }
  button { padding: 10px 14px; border-radius: 6px; border: 1px solid #28536b; background: #133349; color: #e6f1ff; cursor: pointer; }
  button.active { background: #1a4a65; }
  button:hover { background: #16425a; }
  pre { background: #0c2230; padding: 12px; border-radius: 8px; border: 1px solid #28536b; white-space: pre-wrap; }
  .status { font-size: 12px; opacity: 0.8; }
</style>
</head>
<body>
<header>
  <h1>🐟 Sakana Desktop Assistant</h1>
  <div class="status">GUI connected to http://$HOST:$PORT</div>
</header>
<main>
  <div class="row">
    <input id="chat-input" type="text" placeholder="Type a message…" />
    <button id="send-btn">Send</button>
    <button id="plugins" title="List available plugins">Plugins</button>
  </div>
  <div id="chat-log"></div>
</main>
<script>
  const msg = document.getElementById('chat-input');
  const out = document.getElementById('chat-log');
  const send = document.getElementById('send-btn');
  
  async function postJSON(path, payload) {
    const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    return await res.json();
  }
  
  send.addEventListener('click', async () => {
    const text = msg.value.trim();
    if (!text) return;
    out.textContent = 'Thinking...';
    try {
      const r = await postJSON('/api/message', { input: text });
      out.textContent = JSON.stringify(r, null, 2);
    } catch (e) {
      out.textContent = 'Error: ' + e;
    }
  });
  
  document.getElementById('plugins').addEventListener('click', async () => {
    out.textContent = 'Loading plugins...';
    try {
      const r = await fetch('/api/plugins');
      const j = await r.json();
      out.textContent = JSON.stringify(j, null, 2);
    } catch (e) {
      out.textContent = 'Error: ' + e;
    }
  });
  
  try {
    const es = new EventSource('/events');
    es.addEventListener('reload', () => { location.reload(); });
  } catch (e) { }
</script>
</body>
</html>
"""
        try:
            return html.replace("$HOST", str(self.host)).replace("$PORT", str(self.port))
        except Exception:
            logger.exception("Failed to substitute HOST/PORT in INDEX_HTML; returning raw HTML")
            return html