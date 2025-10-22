from typing import Any

def proxy_session_sse(handler: Any, session_host: str, session_port: int, remaining_path: str = "/events") -> None:
    """Proxy SSE stream from upstream Playwright session server to the client.
    Keeps the server-sent events channel open and pipes chunks transparently.

    Parameters:
    - handler: Request handler with send_response, send_header, end_headers, wfile
    - session_host/port: Upstream Playwright server location
    - remaining_path: Path to request on upstream (e.g., '/events' or '/events?...')
    """
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()

        import http.client
        conn = http.client.HTTPConnection(session_host, int(session_port), timeout=10)
        conn.request("GET", remaining_path, headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        resp = conn.getresponse()

        if resp.status == 200:
            while True:
                try:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    try:
                        handler.wfile.write(chunk)
                        handler.wfile.flush()
                    except (ConnectionAbortedError, BrokenPipeError):
                        return
                    except Exception:
                        return
                except (ConnectionAbortedError, BrokenPipeError):
                    return
                except Exception:
                    return
            return
        else:
            # Write minimal error to SSE stream
            try:
                handler.wfile.write(f"data: Proxy upstream error HTTP {resp.status}\n\n".encode("utf-8"))
                handler.wfile.flush()
            except Exception:
                pass
            return
    except Exception as e:
        try:
            handler._json(502, {"error": f"Session upstream failed: {e}"})
        except Exception:
            pass
        return

def proxy_session_preview_png(handler: Any, session_host: str, session_port: int, remaining_path: str = "/preview.png") -> None:
    """Proxy preview.png from upstream Playwright session server to the client.

    Parameters:
    - handler: Request handler with send_response, send_header, end_headers, wfile
    - session_host/port: Upstream Playwright server location
    - remaining_path: Path to request on upstream (e.g., '/preview.png' or '/preview.png?...')
    """
    try:
        import urllib.request, urllib.error
        from urllib.parse import urlparse

        # Preserve query string from original request path if present
        upstream_path = remaining_path
        try:
            parsed = urlparse(getattr(handler, 'path', remaining_path))
            if parsed.query:
                upstream_path += ("?" + parsed.query)
        except Exception:
            pass

        url = f"http://{session_host}:{session_port}{upstream_path}"
        req = urllib.request.Request(url, headers={"Accept": "image/png, */*"})
        with urllib.request.urlopen(req, timeout=2.0) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "image/png")
            status = getattr(r, "status", 200)
            handler.send_response(status)
            handler.send_header("Content-Type", ctype)
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            try:
                handler.wfile.write(body)
            except (ConnectionAbortedError, BrokenPipeError):
                return
            except Exception:
                return
        return
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read() if hasattr(e, "read") else b""
        except Exception:
            err_body = b""
        ctype = e.headers.get("Content-Type", "application/json; charset=utf-8") if hasattr(e, "headers") else "application/octet-stream"
        try:
            handler.send_response(e.code)
            handler.send_header("Content-Type", ctype)
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("Content-Length", str(len(err_body)))
            handler.end_headers()
            handler.wfile.write(err_body)
        except Exception:
            pass
        return
    except Exception as e:
        try:
            handler._json(502, {"error": f"Session preview upstream failed: {e}"})
        except Exception:
            pass
        return