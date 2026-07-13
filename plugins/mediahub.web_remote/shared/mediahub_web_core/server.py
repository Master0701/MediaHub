from __future__ import annotations

import inspect
import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


@dataclass
class RequestContext:
    path: str
    method: str
    headers: dict[str, str]
    client_ip: str

    @property
    def bearer_token(self) -> str:
        value = self.headers.get("authorization", "")
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return ""


class LocalWebServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, *, auth_callback: Callable[[RequestContext], bool] | None = None, public_paths: set[str] | None = None):
        self.host = host
        self.port = int(port)
        self.auth_callback = auth_callback
        self.public_paths = set(public_paths or {"/"})
        self.routes: dict[str, Callable] = {}
        self.post_routes: dict[str, Callable] = {}
        self._server = None
        self._thread = None

    def add_route(self, path, callback):
        self.routes[path] = callback

    def add_post_route(self, path, callback):
        self.post_routes[path] = callback

    @staticmethod
    def _invoke(callback: Callable, *args):
        try:
            signature = inspect.signature(callback)
            count = len(signature.parameters)
        except (TypeError, ValueError):
            count = len(args)
        return callback(*args[:count])

    def _handler_class(self):
        owner = self

        class RequestHandler(BaseHTTPRequestHandler):
            def _context(self) -> RequestContext:
                path = self.path.split("?", 1)[0]
                return RequestContext(
                    path=path,
                    method=self.command,
                    headers={str(k).lower(): str(v) for k, v in self.headers.items()},
                    client_ip=str(self.client_address[0] if self.client_address else ""),
                )

            def _write(self, status: int, content_type: str, body: bytes):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                self.close_connection = True

            def _authorized(self, context: RequestContext) -> bool:
                if context.path in owner.public_paths or owner.auth_callback is None:
                    return True
                try:
                    return bool(owner.auth_callback(context))
                except Exception:
                    return False

            def do_GET(self):
                context = self._context()
                route = owner.routes.get(context.path)
                if not route:
                    return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
                if not self._authorized(context):
                    return self._write(401, "application/json; charset=utf-8", json.dumps({"ok": False, "error": "pairing_required", "message": "Dieses Gerät muss zuerst gekoppelt werden."}, ensure_ascii=False).encode("utf-8"))
                try:
                    self._write(*owner._invoke(route, context))
                except Exception as error:
                    self._write(500, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}).encode("utf-8"))

            def do_POST(self):
                context = self._context()
                route = owner.post_routes.get(context.path)
                if not route:
                    return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
                if not self._authorized(context):
                    return self._write(401, "application/json; charset=utf-8", json.dumps({"ok": False, "error": "pairing_required", "message": "Dieses Gerät muss zuerst gekoppelt werden."}, ensure_ascii=False).encode("utf-8"))
                try:
                    length = min(int(self.headers.get("Content-Length", "0") or 0), 1048576)
                    payload = json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("JSON-Objekt erwartet")
                    self._write(*owner._invoke(route, payload, context))
                except Exception as error:
                    self._write(400, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}).encode("utf-8"))

            def log_message(self, format, *args):
                return

        return RequestHandler

    def start(self):
        if self._server is not None:
            return
        self._server = ThreadingHTTPServer((self.host, self.port), self._handler_class())
        self._thread = threading.Thread(target=self._server.serve_forever, name="MediaHubWebRuntime", daemon=True)
        self._thread.start()

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    @property
    def running(self):
        return self._server is not None
