from typing import Any


def proxy_json_events(handler: Any, session_host: str, session_port: int, upstream_path_with_query: str = "/events.json") -> None:
    """Proxy JSON polling from an upstream Playwright server.

    Writes the JSON body back to the client, preserving Content-Type and status.
    Falls back gracefully if the handler doesn't expose backoff helpers.
    """
    try:
        from urllib.parse import urlparse  # noqa: F401
        import urllib.request, urllib.error
    except Exception:
        urllib = None  # type: ignore

    # Build URL
    url = f"http://{session_host}:{int(session_port)}{upstream_path_with_query}"

    try:
        if urllib is None:
            raise RuntimeError("urllib unavailable")

        req = urllib.request.Request(url, headers={"Accept": "application/json"})

        # Use handler's backoff helper if available
        backoff = getattr(handler, "_fetch_with_backoff", None)
        if callable(backoff):
            rctx = backoff(req, timeout=2.5, attempts=4, base_delay=0.25)
            # Context manager returns an object with .read() and .headers
            with rctx as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
                status = getattr(r, "status", 200)
                handler.send_response(status)
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
                return
        else:
            with urllib.request.urlopen(req, timeout=2.5) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
                # urllib response doesn't guarantee .status across versions; default to 200
                status = getattr(r, "status", 200)
                handler.send_response(int(status))
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
                return
    except Exception as e:
        try:
            handler._json(502, {"error": f"Upstream JSON events proxy failed: {e}"})
        except Exception:
            pass