from __future__ import annotations
from pathlib import Path
from typing import Any
from mimetypes import guess_type


def try_serve_spa(handler: Any, clean_path: str | None = None) -> bool:
    """Serve React SPA assets and index.html fallback if enabled.

    Returns True if the request was handled, False otherwise.
    Designed to be importable and removable independently.
    """
    try:
        srv = getattr(handler, 'server', None)
        react_enabled = bool(getattr(srv, '_react_ui_enabled', False))
        dist_dir = getattr(srv, '_react_ui_dist_dir', None)
    except Exception:
        react_enabled = False
        dist_dir = None

    if not react_enabled or not dist_dir:
        return False

    try:
        dist_root = Path(dist_dir).resolve()
        req_path = (clean_path or handler.path or '/').split('?', 1)[0]

        def _is_api_path(p: str) -> bool:
            return p.startswith('/api/') or p.startswith('/events') or p.startswith('/mcp/')

        if req_path == '/' or req_path.startswith('/index.html'):
            index_fp = dist_root / 'index.html'
            if index_fp.is_file():
                body = index_fp.read_bytes()
                handler.send_response(200)
                handler.send_header('Content-Type', 'text/html; charset=utf-8')
                handler.send_header('Content-Length', str(len(body)))
                handler.end_headers()
                try:
                    handler.wfile.write(body)
                except Exception:
                    pass
                return True
        elif not _is_api_path(req_path):
            # Serve static asset if present, else SPA fallback
            rel = req_path.lstrip('/')
            try:
                fs_path = (dist_root / rel).resolve()
                if str(fs_path).startswith(str(dist_root)) and fs_path.is_file():
                    body = fs_path.read_bytes()
                    ctype = guess_type(str(fs_path))[0] or 'application/octet-stream'
                    handler.send_response(200)
                    handler.send_header('Content-Type', ctype)
                    handler.send_header('Content-Length', str(len(body)))
                    handler.end_headers()
                    try:
                        handler.wfile.write(body)
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
            # Fallback to index.html
            index_fp = dist_root / 'index.html'
            if index_fp.is_file():
                body = index_fp.read_bytes()
                handler.send_response(200)
                handler.send_header('Content-Type', 'text/html; charset=utf-8')
                handler.send_header('Content-Length', str(len(body)))
                handler.end_headers()
                try:
                    handler.wfile.write(body)
                except Exception:
                    pass
                return True
    except Exception:
        # Let caller continue with legacy handling on any error
        return False

    return False