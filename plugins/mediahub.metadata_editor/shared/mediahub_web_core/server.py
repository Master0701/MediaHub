from __future__ import annotations

import inspect
import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Any


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


@dataclass
class RouteEntry:
    callback: Callable
    auth_callback: Callable[[RequestContext], bool] | None = None
    owner: Any = None


class LocalWebServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = int(port)
        self.routes: dict[str, RouteEntry] = {}
        self.post_routes: dict[str, RouteEntry] = {}
        self.fallback_routes: dict[str, RouteEntry] = {}
        self._server = None
        self._thread = None
        self._route_lock = threading.RLock()

    def add_route(self, path, callback, *, auth_callback=None, owner=None):
        with self._route_lock:
            self.routes[path] = RouteEntry(callback, auth_callback, owner)

    def add_post_route(self, path, callback, *, auth_callback=None, owner=None):
        with self._route_lock:
            self.post_routes[path] = RouteEntry(callback, auth_callback, owner)

    def add_fallback_route(self, path, callback, *, auth_callback=None, owner=None):
        """Route, die nur verwendet wird, wenn keine normale Route existiert."""
        with self._route_lock:
            self.fallback_routes[path] = RouteEntry(callback, auth_callback, owner)

    def remove_routes(self, owner):
        with self._route_lock:
            self.routes = {path: entry for path, entry in self.routes.items() if entry.owner is not owner}
            self.post_routes = {path: entry for path, entry in self.post_routes.items() if entry.owner is not owner}
            self.fallback_routes = {path: entry for path, entry in self.fallback_routes.items() if entry.owner is not owner}

    @staticmethod
    def _invoke(callback: Callable, *args):
        try:
            signature = inspect.signature(callback)
            count = len(signature.parameters)
        except (TypeError, ValueError):
            count = len(args)
        return callback(*args[:count])

    @staticmethod
    def _authorized(entry: RouteEntry, context: RequestContext) -> bool:
        if entry.auth_callback is None:
            return True
        try:
            return bool(entry.auth_callback(context))
        except Exception:
            return False

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

            def _entry(self, table):
                path = self.path.split("?", 1)[0]
                with owner._route_lock:
                    entry = table.get(path)
                    if entry is None and table is owner.routes:
                        entry = owner.fallback_routes.get(path)
                    return entry

            def do_GET(self):
                context = self._context()
                entry = self._entry(owner.routes)
                if not entry:
                    return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
                if not owner._authorized(entry, context):
                    return self._write(401, "application/json; charset=utf-8", json.dumps({"ok": False, "error": "pairing_required", "message": "Dieses Gerät muss zuerst gekoppelt werden."}, ensure_ascii=False).encode("utf-8"))
                try:
                    self._write(*owner._invoke(entry.callback, context))
                except Exception as error:
                    self._write(500, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False).encode("utf-8"))

            def do_POST(self):
                context = self._context()
                entry = self._entry(owner.post_routes)
                if not entry:
                    return self._write(404, "application/json; charset=utf-8", b'{"error":"not_found"}')
                if not owner._authorized(entry, context):
                    return self._write(401, "application/json; charset=utf-8", json.dumps({"ok": False, "error": "pairing_required", "message": "Dieses Gerät muss zuerst gekoppelt werden."}, ensure_ascii=False).encode("utf-8"))
                try:
                    length = min(int(self.headers.get("Content-Length", "0") or 0), 1048576)
                    payload = json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("JSON-Objekt erwartet")
                    self._write(*owner._invoke(entry.callback, payload, context))
                except Exception as error:
                    self._write(400, "application/json; charset=utf-8", json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False).encode("utf-8"))

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

    def restart(self, host: str, port: int):
        was_running = self.running
        self.stop()
        self.host = str(host)
        self.port = int(port)
        if was_running:
            self.start()

    @property
    def running(self):
        return self._server is not None


_SHARED_LOCK = threading.RLock()
_SHARED_SERVERS: dict[str, dict] = {}


def acquire_shared_server(key: str, host: str, port: int) -> LocalWebServer:
    """Eine Serverinstanz pro MediaHub-Laufzeit, gemeinsam für alle Web-Plugins."""
    normalized = str(key)
    with _SHARED_LOCK:
        item = _SHARED_SERVERS.get(normalized)
        if item is not None:
            server = item["server"]
            if server.host != host or int(server.port) != int(port):
                server.restart(host, port)
            item["references"] += 1
            return server
        server = LocalWebServer(host=host, port=port)
        _SHARED_SERVERS[normalized] = {"server": server, "references": 1}
        return server


def release_shared_server(key: str, owner=None) -> None:
    normalized = str(key)
    with _SHARED_LOCK:
        item = _SHARED_SERVERS.get(normalized)
        if item is None:
            return
        if owner is not None:
            item["server"].remove_routes(owner)
        item["references"] = max(0, int(item.get("references", 1)) - 1)
        server = item["server"]
        # Solange ein anderes Plugin noch Routen registriert hat, bleibt die
        # gemeinsame Serverinstanz aktiv – auch wenn ein Referenzzähler durch
        # Reloads oder Plugin-Austausch kurzzeitig nicht mehr exakt ist.
        has_routes = bool(server.routes or server.post_routes or server.fallback_routes)
        if item["references"] <= 0 and not has_routes:
            server.stop()
            _SHARED_SERVERS.pop(normalized, None)
