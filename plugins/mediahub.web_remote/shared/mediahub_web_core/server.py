from __future__ import annotations
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
class _RequestHandler(BaseHTTPRequestHandler):
    routes: dict[str, Callable] = {}; post_routes: dict[str, Callable] = {}
    def _write(self,s,c,b):
        self.send_response(s); self.send_header("Content-Type",c); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        r=self.routes.get(self.path.split("?",1)[0])
        if not r: return self._write(404,"application/json; charset=utf-8",b'{"error":"not_found"}')
        try: self._write(*r())
        except Exception as e: self._write(500,"application/json; charset=utf-8",json.dumps({"ok":False,"error":str(e)}).encode())
    def do_POST(self):
        r=self.post_routes.get(self.path.split("?",1)[0])
        if not r: return self._write(404,"application/json; charset=utf-8",b'{"error":"not_found"}')
        try:
            n=min(int(self.headers.get("Content-Length","0") or 0),1048576); p=json.loads((self.rfile.read(n) if n else b"{}").decode())
            if not isinstance(p,dict): raise ValueError("JSON-Objekt erwartet")
            self._write(*r(p))
        except Exception as e: self._write(400,"application/json; charset=utf-8",json.dumps({"ok":False,"error":str(e)}).encode())
    def log_message(self,format,*args): return
class LocalWebServer:
    def __init__(self,host="127.0.0.1",port=8765): self.host=host; self.port=port; self._server=None; self._thread=None
    def add_route(self,path,callback): _RequestHandler.routes[path]=callback
    def add_post_route(self,path,callback): _RequestHandler.post_routes[path]=callback
    def start(self):
        if self._server is not None:return
        self._server=ThreadingHTTPServer((self.host,self.port),_RequestHandler); self._thread=threading.Thread(target=self._server.serve_forever,daemon=True); self._thread.start()
    def stop(self):
        if self._server is None:return
        self._server.shutdown(); self._server.server_close(); self._server=None; self._thread=None
    @property
    def running(self): return self._server is not None
