"""Visual GUI launcher for the SamboTL server (pywebview).

Shows, before and after starting the server:
  * the list of tournaments (with the active one highlighted);
  * the create-tournament form (system, audience, mats, password, admin);
  * the access password and admin credentials in plain sight;
  * Start / Stop / Open-browser controls and the LAN address.

The actual Django server runs as a background subprocess (``--run``), so the
GUI itself never holds Django state and Stop simply terminates the child.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import webview

if getattr(sys, "frozen", False):
    _BUNDLE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    UI_FILE = _BUNDLE / "launcher" / "server_gui.html"
    EXECUTABLE = Path(sys.executable).resolve()
else:
    UI_FILE = Path(__file__).resolve().parent / "server_gui.html"
    EXECUTABLE = Path(sys.executable).resolve()
    # From source we can re-enter this module.
    EXECUTABLE = Path(__file__).resolve().parent / "server.py"


def _server_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(EXECUTABLE)]
    return [sys.executable, str(EXECUTABLE)]


def _lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _run_subprocess(args: list[str]) -> dict:
    """Run a one-shot management command and parse its JSON stdout."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}
    stdout = (result.stdout or "").strip()
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": (result.stderr or stdout or "нет вывода")}


def _settings_path() -> Path:
    """Local, writable cache of operator-facing credentials (next to the exe).

    Passwords are only stored hashed inside Django; this file keeps the plain
    values so the panel can remind the operator. It lives on the organiser's
    own server PC, which is the same trust boundary as the tournament database.
    """
    base = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent.parent
    )
    target = base / "data"
    target.mkdir(parents=True, exist_ok=True)
    return target / "server_credentials.json"


def _load_settings() -> dict:
    path = _settings_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_settings(data: dict) -> None:
    path = _settings_path()
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:  # pragma: no cover
        pass


class ServerBridge:
    def __init__(self) -> None:
        self.process = None
        self.port = 8000
        self.host = "0.0.0.0"

    # ---- tournaments ------------------------------------------------------
    def list_tournaments(self) -> list:
        data = _run_subprocess(_server_command() + ["--list-tournaments"])
        if not isinstance(data, list):
            return []
        credentials = _load_settings()
        for entry in data:
            stored = credentials.get(entry.get("slug") or "", {})
            entry["access_password"] = stored.get("access_password", "")
            entry["admin_password"] = stored.get("admin_password", "")
        return data

    def create_tournament(self, name, system, audience, mats, password, admin_password) -> dict:
        payload = json.dumps(
            {
                "name": name,
                "system": system,
                "audience": audience,
                "mats": int(mats),
                "password": password,
                "admin_password": admin_password,
            },
            ensure_ascii=False,
        )
        result = _run_subprocess(_server_command() + ["--create-tournament", payload])
        if result.get("ok") and result.get("slug"):
            credentials = _load_settings()
            credentials[result["slug"]] = {
                "access_password": password or "",
                "admin_password": admin_password or "admin1234",
            }
            _save_settings(credentials)
        return result

    def select_tournament(self, slug: str) -> dict:
        return _run_subprocess(_server_command() + ["--select", slug])

    def credentials_for(self, slug: str) -> dict:
        """Return the stored plain-text credentials for a tournament."""
        stored = _load_settings().get(slug) or {}
        return {
            "access_password": stored.get("access_password", ""),
            "admin_password": stored.get("admin_password", ""),
        }

    def active_credentials(self) -> dict:
        for entry in self.list_tournaments():
            if entry.get("active"):
                return {
                    "slug": entry.get("slug"),
                    "name": entry.get("name"),
                    "access_password": entry.get("access_password", ""),
                    "admin_password": entry.get("admin_password", ""),
                }
        return {}

    def set_access_password(self, slug: str, password: str) -> dict:
        """Change the shared client password of an existing tournament."""
        result = _run_subprocess(
            _server_command()
            + ["--set-access-password", slug, "--value", password or ""]
        )
        if result.get("ok"):
            credentials = _load_settings()
            entry = credentials.setdefault(slug, {})
            entry["access_password"] = password or ""
            _save_settings(credentials)
        return result

    def set_admin_password(self, slug: str, password: str) -> dict:
        result = _run_subprocess(
            _server_command() + ["--set-admin-password", slug, "--value", password or ""]
        )
        if result.get("ok"):
            credentials = _load_settings()
            entry = credentials.setdefault(slug, {})
            entry["admin_password"] = password or ""
            _save_settings(credentials)
        return result

    # ---- server lifecycle -------------------------------------------------
    def start_server(self, port, host) -> dict:
        if self.process is not None and self.process.poll() is None:
            return {"ok": False, "error": "Сервер уже запущен"}
        self.port = int(port)
        self.host = host or "0.0.0.0"
        args = _server_command() + ["--run", str(self.port), "--host", self.host]
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        # Wait until it answers on the port.
        for _ in range(60):
            if self.process.poll() is not None:
                return {"ok": False, "error": "Сервер не смог запуститься"}
            if self._is_alive():
                return {"ok": True, "lan_ip": _lan_ip(), "port": self.port}
            time.sleep(0.5)
        return {"ok": False, "error": "Таймаут запуска сервера"}

    def stop_server(self) -> dict:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None
        return {"ok": True}

    def server_status(self) -> dict:
        running = self.process is not None and self.process.poll() is None
        return {"running": running, "lan_ip": _lan_ip(), "port": self.port}

    def open_browser(self, path: str = "/app/") -> dict:
        webbrowser.open(f"http://127.0.0.1:{self.port}{path}")
        return {"ok": True}

    def open_admin(self) -> dict:
        return self.open_browser("/admin/")

    def _is_alive(self) -> bool:
        import urllib.request

        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/health/", timeout=2
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def on_close(self) -> None:
        self.stop_server()


def run_gui() -> int:
    bridge = ServerBridge()
    window = webview.create_window(
        "SamboTL — панель сервера",
        url=str(UI_FILE),
        js_api=bridge,
        width=880,
        height=760,
        min_size=(700, 560),
        background_color="#0f172a",
    )
    window.events.closed += bridge.on_close
    webview.start()
    return 0
