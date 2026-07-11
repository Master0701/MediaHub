from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

from mediahub_web_core.server import LocalWebServer


class MediaHubWebRemotePlugin:
    VERSION = "0.8.1"

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.server = LocalWebServer(host="127.0.0.1", port=8765)
        self._activity_lock = threading.Lock()
        self._activities = deque(maxlen=100)
        self._last_connected = None
        self._last_download_signature = None
        self._last_done_count = 0
        routes = {
            "/": self._index,
            "/api/status": self._status,
            "/api/dashboard": self._dashboard,
            "/api/channels": self._channels,
            "/api/playlists": self._playlists,
            "/api/library": self._library,
            "/api/downloads": self._downloads,
            "/api/jobs": self._jobs,
            "/api/scheduler": self._scheduler,
            "/api/statistics": self._statistics,
            "/api/plugins": self._plugins,
            "/api/system": self._system,
            "/api/activities": self._activity_feed,
        }
        for path, handler in routes.items():
            self.server.add_route(path, handler)
        self.server.add_post_route("/api/action", self._action)
        self._add_activity("system", "WebRemote gestartet", "Das lokale Lese-Control-Center ist bereit.", "info")

    def start(self):
        self.server.start()

    def stop(self):
        self._add_activity("system", "WebRemote beendet", "Der lokale Webserver wird gestoppt.", "info")
        self.server.stop()

    def _index(self):
        return 200, "text/html; charset=utf-8", (self.plugin_path / "index.html").read_bytes()

    def _json(self, data, status=200):
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _api_call(self, method, default):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, method):
            return default, False, f"{method} ist in dieser MediaHub-Version nicht verfügbar."
        try:
            return getattr(self.mediahub_api, method)(), True, ""
        except Exception as error:
            return default, False, str(error)

    def _add_activity(self, category, title, detail="", level="info"):
        item = {"time": datetime.now().isoformat(timespec="seconds"), "category": category,
                "title": title, "detail": detail, "level": level}
        with self._activity_lock:
            self._activities.appendleft(item)

    def _read_status(self):
        if self.mediahub_api is None:
            return {"connected": False, "channels": 0, "playlists": 0, "videos": 0}
        return self.mediahub_api.get_status()

    def _observe_status(self, mediahub):
        connected = bool(mediahub.get("connected"))
        if self._last_connected is None:
            self._last_connected = connected
            self._add_activity("connection", "MediaHub verbunden" if connected else "MediaHub nicht verbunden",
                               level="success" if connected else "warning")
        elif connected != self._last_connected:
            self._last_connected = connected
            self._add_activity("connection", "MediaHub verbunden" if connected else "Verbindung zu MediaHub verloren",
                               level="success" if connected else "error")

    def _observe_download(self, data):
        active = bool(data.get("active")); title = str(data.get("current_title") or "")
        done = int(data.get("done_count") or 0); total = int(data.get("total_count") or 0)
        status = str(data.get("status") or ""); signature = (active, title, status, total)
        if self._last_download_signature is None:
            self._last_download_signature = signature; self._last_done_count = done
            if active: self._add_activity("download", "Download läuft", title or status, "success")
            return
        old_active, old_title, _, _ = self._last_download_signature
        if active and (not old_active or title != old_title):
            self._add_activity("download", "Download gestartet", title or "Unbekanntes Video", "success")
        if old_active and not active:
            self._add_activity("download", "Download beendet", old_title or status, "success")
        if done > self._last_done_count:
            self._add_activity("download", "Video abgeschlossen", f"{done} von {total} erledigt", "success")
        self._last_download_signature = signature; self._last_done_count = done

    def _status(self):
        mediahub = self._read_status(); self._observe_status(mediahub)
        return self._json({"product": "MediaHub WebRemote", "version": self.VERSION,
                           "server": "online", "scope": "computer_only", "mode": "read_write_controlled", "mediahub": mediahub})

    def _dashboard(self):
        data, ok, message = self._api_call("get_dashboard_details", {})
        return self._json({"available": ok, "data": data, "message": message})

    def _channels(self):
        data, ok, message = self._api_call("get_channels", [])
        return self._json({"available": ok, "channels": data, "count": len(data), "message": message})

    def _playlists(self):
        data, ok, message = self._api_call("get_playlists", [])
        return self._json({"available": ok, "playlists": data, "count": len(data), "message": message})

    def _library(self):
        data, ok, message = self._api_call("get_library_videos", [])
        return self._json({"available": ok, "videos": data, "count": len(data), "message": message})

    def _jobs(self):
        data, ok, message = self._api_call("get_jobs", [])
        return self._json({"available": ok, "jobs": data, "count": len(data), "message": message})

    def _scheduler(self):
        data, ok, message = self._api_call("get_scheduler_tasks", [])
        return self._json({"available": ok, "tasks": data, "count": len(data), "message": message})

    def _statistics(self):
        data, ok, message = self._api_call("get_statistics_summary", {})
        return self._json({"available": ok, "statistics": data, "message": message})

    def _system(self):
        data, ok, message = self._api_call("get_system_overview", {})
        return self._json({"available": ok, "system": data, "message": message})

    def _plugins(self):
        data, ok, message = self._api_call("get_installed_plugins", [])
        if not ok:
            data = [{"id": "mediahub.web_remote", "name": "WebRemote", "version": self.VERSION,
                     "installed": True, "enabled": True, "running": True}]
        for item in data:
            if item.get("id") == "mediahub.web_remote":
                item["running"] = True; item["version"] = self.VERSION
        return self._json({"available": True, "plugins": data, "count": len(data), "message": message})

    def _downloads(self):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "get_download_status"):
            return self._json({"available": False, "active": False, "message": "Downloadstatus nicht verfügbar.", "queue": []})
        try:
            data = self.mediahub_api.get_download_status(); data["available"] = True
            self._observe_download(data); return self._json(data)
        except Exception as error:
            return self._json({"available": False, "active": False, "message": str(error), "queue": []}, status=500)


    def _action(self, payload):
        action = str(payload.get("action") or "").strip()
        args = payload.get("payload") or {}
        allowed = {"assistant.open","plugins.open","channels.sync","channels.sync_current","downloads.cancel","downloads.select_videos","downloads.select_playlists","jobs.run_next","scheduler.check","scheduler.toggle"}
        if action not in allowed:
            return self._json({"ok": False, "message": "Aktion ist nicht freigegeben."}, status=403)
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "execute_action"):
            return self._json({"ok": False, "message": "MediaHub Write-API Fix 5 ist erforderlich."}, status=409)
        result = self.mediahub_api.execute_action(action, args)
        if not isinstance(result, dict): result = {"ok": bool(result), "message": "Aktion angenommen."}
        self._add_activity("action", action, str(result.get("message") or ""), "success" if result.get("ok") else "error")
        return self._json(result, status=200 if result.get("ok") else 409)

    def _activity_feed(self):
        try:
            self._observe_status(self._read_status())
            if self.mediahub_api is not None and hasattr(self.mediahub_api, "get_download_status"):
                self._observe_download(self.mediahub_api.get_download_status())
        except Exception:
            pass
        with self._activity_lock: items = list(self._activities)
        return self._json({"available": True, "source": "webremote_observer", "activities": items, "count": len(items)})
