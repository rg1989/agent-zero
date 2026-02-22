"""
App Manager — manages local web apps built by Agent Zero.

Apps live in {project_root}/apps/{name}/ and are served on an inner port
(9000-9099 by default). The proxy in app_proxy.py routes
localhost:50000/{name}/... → localhost:{inner_port}/...
"""

import json
import os
import signal
import subprocess
import threading
import time
from typing import Optional

from python.helpers.files import get_abs_path

APPS_DIR = get_abs_path("./apps")
REGISTRY_FILE = os.path.join(APPS_DIR, ".app_registry.json")

PORT_RANGE_START = 9000
PORT_RANGE_END = 9099

_lock = threading.RLock()


class AppManager:
    _instance: Optional["AppManager"] = None

    def __init__(self):
        self._registry: dict[str, dict] = {}
        os.makedirs(APPS_DIR, exist_ok=True)
        self._load_registry()

    @classmethod
    def get_instance(cls) -> "AppManager":
        with _lock:
            if cls._instance is None:
                cls._instance = AppManager()
            return cls._instance

    # ──────────────────────────────────────────────
    # Registry persistence
    # ──────────────────────────────────────────────

    def _load_registry(self) -> None:
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE) as f:
                    self._registry = json.load(f)
            except Exception:
                self._registry = {}
        self._cleanup_dead_processes()

    def _save_registry(self) -> None:
        os.makedirs(APPS_DIR, exist_ok=True)
        with open(REGISTRY_FILE, "w") as f:
            json.dump(self._registry, f, indent=2)

    # ──────────────────────────────────────────────
    # Process helpers
    # ──────────────────────────────────────────────

    def _is_pid_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _cleanup_dead_processes(self) -> None:
        changed = False
        for info in self._registry.values():
            if info.get("status") == "running":
                pid = info.get("pid")
                if pid and not self._is_pid_running(pid):
                    info["status"] = "stopped"
                    info["pid"] = None
                    changed = True
        if changed:
            self._save_registry()

    # ──────────────────────────────────────────────
    # Port allocation
    # ──────────────────────────────────────────────

    def next_available_port(self) -> int:
        with _lock:
            self._cleanup_dead_processes()
            used = {info["port"] for info in self._registry.values()}
            for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
                if port not in used:
                    return port
            raise RuntimeError(
                f"No available ports in range {PORT_RANGE_START}-{PORT_RANGE_END}"
            )

    # ──────────────────────────────────────────────
    # App lifecycle
    # ──────────────────────────────────────────────

    def autostart_all(self) -> list[str]:
        """Start all apps that have autostart=True. Called once at server startup."""
        started = []
        with _lock:
            self._cleanup_dead_processes()
            for name, info in list(self._registry.items()):
                if info.get("autostart") and info.get("status") != "running":
                    try:
                        self.start_app(name)
                        started.append(name)
                    except Exception as e:
                        from python.helpers.print_style import PrintStyle
                        PrintStyle.warning(f"[AppManager] autostart failed for '{name}': {e}")
        return started

    def set_autostart(self, name: str, enabled: bool) -> dict:
        """Enable or disable autostart for a registered app."""
        with _lock:
            info = self._registry.get(name)
            if not info:
                raise KeyError(f"App '{name}' not registered")
            self._registry[name]["autostart"] = enabled
            self._save_registry()
            return dict(self._registry[name])

    def register_app(
        self,
        name: str,
        port: int,
        cmd: str,
        cwd: str,
        description: str = "",
        env: Optional[dict] = None,
        autostart: bool = False,
        ws_port: Optional[int] = None,
    ) -> dict:
        """Register an app. Does not start it.

        ws_port: if set, WebSocket connections to /{name}/... are forwarded to
        this port instead of port. Useful for apps that run a WebSocket service
        (e.g. websockify for VNC) on a separate port from their HTTP server.
        """
        with _lock:
            entry: dict = {
                "name": name,
                "port": port,
                "cmd": cmd,
                "cwd": cwd,
                "description": description,
                "env": env or {},
                "autostart": autostart,
                "status": "registered",
                "pid": None,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "url": f"/{name}/",
            }
            if ws_port is not None:
                entry["ws_port"] = ws_port
            self._registry[name] = entry
            self._save_registry()
            return dict(self._registry[name])

    def start_app(self, name: str) -> dict:
        """Start a registered app as a background process."""
        with _lock:
            info = self._registry.get(name)
            if not info:
                raise KeyError(f"App '{name}' not registered")

            # Kill existing process if still alive
            pid = info.get("pid")
            if pid and self._is_pid_running(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
                    if self._is_pid_running(pid):
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            cwd = info["cwd"]
            os.makedirs(cwd, exist_ok=True)

            # Merge environment
            env = os.environ.copy()
            env.update(info.get("env", {}))
            env["PORT"] = str(info["port"])
            env["APP_NAME"] = name  # used by templates for <base href="/APP_NAME/">

            proc = subprocess.Popen(
                info["cmd"],
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            self._registry[name]["pid"] = proc.pid
            self._registry[name]["status"] = "running"
            self._registry[name]["started_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            self._save_registry()
            return dict(self._registry[name])

    def stop_app(self, name: str) -> dict:
        """Stop a running app."""
        with _lock:
            info = self._registry.get(name)
            if not info:
                raise KeyError(f"App '{name}' not registered")

            pid = info.get("pid")
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)
                    if self._is_pid_running(pid):
                        os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass

            self._registry[name]["status"] = "stopped"
            self._registry[name]["pid"] = None
            self._save_registry()
            return dict(self._registry[name])

    def remove_app(self, name: str) -> bool:
        """Stop and unregister an app."""
        with _lock:
            if name not in self._registry:
                return False
            try:
                self.stop_app(name)
            except Exception:
                pass
            del self._registry[name]
            self._save_registry()
            return True

    def restart_app(self, name: str) -> dict:
        """Stop then start an app."""
        self.stop_app(name)
        time.sleep(1)
        return self.start_app(name)

    # ──────────────────────────────────────────────
    # Query
    # ──────────────────────────────────────────────

    def get_app(self, name: str) -> Optional[dict]:
        with _lock:
            self._cleanup_dead_processes()
            info = self._registry.get(name)
            return dict(info) if info else None

    def list_apps(self) -> list[dict]:
        with _lock:
            self._cleanup_dead_processes()
            return [dict(v) for v in self._registry.values()]

    def is_registered(self, name: str) -> bool:
        return name in self._registry

    def get_port(self, name: str) -> Optional[int]:
        info = self._registry.get(name)
        return info["port"] if info else None

    def apps_dir(self) -> str:
        return APPS_DIR
