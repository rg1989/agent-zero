"""
/webapp — REST API handler for Agent Zero's local web app manager.

Actions (all via POST with JSON body, or GET for read-only actions):

  list          → list all registered apps
  alloc_port    → allocate and return the next available port
  register      → register a new app (does not start it)
  start         → start a registered app
  stop          → stop a running app
  restart       → stop then start an app
  status        → get status of a single app
  remove        → stop and unregister an app

Example (register + start):
  POST /webapp  {"action": "register", "name": "my_app", "port": 9000,
                 "cmd": "python app.py", "cwd": "/a0/apps/my_app",
                 "description": "My dashboard"}
  POST /webapp  {"action": "start", "name": "my_app"}

The app is then accessible at localhost:50000/my_app/
"""

from python.helpers.api import ApiHandler, Request, Response
from python.helpers.app_manager import AppManager


class WebappHandler(ApiHandler):

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False  # agent calls this programmatically without a browser session

    async def process(self, input: dict, request: Request) -> dict | Response:
        # Support GET ?action=list and ?action=status&name=X
        if request.method == "GET":
            action = request.args.get("action", "list")
            name = request.args.get("name", "")
        else:
            action = input.get("action", "list")
            name = input.get("name", "")

        mgr = AppManager.get_instance()

        if action == "list":
            return {"apps": mgr.list_apps(), "apps_dir": mgr.apps_dir()}

        if action == "alloc_port":
            try:
                port = mgr.next_available_port()
                return {"port": port}
            except RuntimeError as e:
                return {"error": str(e)}

        if action == "status":
            if not name:
                return {"error": "name required"}
            info = mgr.get_app(name)
            if info is None:
                return {"error": f"App '{name}' not registered"}
            return {"app": info}

        if action == "register":
            if not name:
                return {"error": "name required"}
            port = input.get("port")
            if port is None:
                return {"error": "port required"}
            cmd = input.get("cmd", "")
            if not cmd:
                return {"error": "cmd required"}
            cwd = input.get("cwd", "")
            if not cwd:
                from python.helpers.app_manager import APPS_DIR
                import os
                cwd = os.path.join(APPS_DIR, name)
            description = input.get("description", "")
            env = input.get("env", {})
            core = bool(input.get("core", False))
            ws_port = input.get("ws_port")
            info = mgr.register_app(
                name=name,
                port=int(port),
                cmd=cmd,
                cwd=cwd,
                description=description,
                env=env,
                core=core,
                ws_port=int(ws_port) if ws_port is not None else None,
            )
            return {"app": info, "url": f"/{name}/"}

        if action == "start":
            if not name:
                return {"error": "name required"}
            try:
                info = mgr.start_app(name)
                return {"app": info, "url": f"/{name}/"}
            except KeyError as e:
                return {"error": str(e)}

        if action == "stop":
            if not name:
                return {"error": "name required"}
            try:
                info = mgr.stop_app(name)
                return {"app": info}
            except KeyError as e:
                return {"error": str(e)}

        if action == "restart":
            if not name:
                return {"error": "name required"}
            try:
                info = mgr.restart_app(name)
                return {"app": info, "url": f"/{name}/"}
            except KeyError as e:
                return {"error": str(e)}

        if action == "remove":
            if not name:
                return {"error": "name required"}
            try:
                removed = mgr.remove_app(name)
                return {"removed": removed, "name": name}
            except ValueError as e:
                return {"error": str(e)}

        if action == "autostart":
            if not name:
                return {"error": "name required"}
            enabled = bool(input.get("enabled", True))
            try:
                info = mgr.set_autostart(name, enabled)
                return {"app": info}
            except KeyError as e:
                return {"error": str(e)}

        return {"error": f"Unknown action: {action}"}
