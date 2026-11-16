"""SamboTL portable client launcher (pywebview).

A small native window with buttons that open the operator screens of the
server found on the LAN. The shared tournament password is injected into the
SPA's localStorage, so the operator types it once per session.

Works from source (``python launcher/client.py``) and as a PyInstaller-frozen
``SamboTL Client.exe`` (portable, no installation required).
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import webview

if getattr(sys, "frozen", False):
    _BUNDLE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    UI_FILE = _BUNDLE / "launcher" / "client_ui.html"
else:
    UI_FILE = Path(__file__).resolve().parent / "client_ui.html"


class Bridge:
    """Python <-> JS bridge exposed as ``window.pywebview.api``."""

    def __init__(self) -> None:
        self.server = "http://127.0.0.1:8000"
        self.password = ""
        self.tournament = ""
        self._target_route = None

    # -- helpers ------------------------------------------------------------
    def _request(self, path: str, password: str) -> dict:
        url = f"{self.server}{path}"
        request = urllib.request.Request(url, headers={"Authorization": f"Token {password}"})
        with urllib.request.urlopen(request, timeout=6) as response:
            return json.loads(response.read().decode("utf-8"))

    # -- API exposed to the UI ---------------------------------------------
    def connect(self, server: str, password: str) -> dict:
        server = (server or "").strip().rstrip("/")
        if not server.startswith("http"):
            server = "http://" + server
        self.server = server
        self.password = password or ""

        try:
            # Validates both reachability and the access password.
            self._request("/api/participants/", self.password)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return {"ok": False, "error": "Неверный пароль доступа"}
            return {"ok": False, "error": f"Сервер ответил ошибкой {exc.code}"}
        except urllib.error.URLError:
            return {"ok": False, "error": "Сервер недоступен. Проверьте адрес и локальную сеть."}
        except Exception as exc:  # pragma: no cover - defensive
            return {"ok": False, "error": f"Ошибка подключения: {exc}"}

        try:
            health = self._request("/api/health/", self.password)
            info = health.get("tournament") or {}
            self.tournament = info.get("name", "")
            return {
                "ok": True,
                "tournament": self.tournament,
                "mats": info.get("mats"),
            }
        except Exception:
            return {"ok": True, "tournament": "", "mats": None}

    def open_screen(self, route: str) -> dict:
        if not self.server:
            return {"ok": False, "error": "Сначала подключитесь к серверу"}
        route = (route or "").strip("/")
        window = webview.windows[0]
        self._target_route = route
        window.load_url(f"{self.server}/app/")
        return {"ok": True}

    def open_admin(self) -> dict:
        import webbrowser

        webbrowser.open(f"{self.server}/admin/")
        return {"ok": True}

    # -- window lifecycle ---------------------------------------------------
    def on_loaded(self) -> None:
        if self._target_route is None:
            return
        route = self._target_route
        self._target_route = None
        window = webview.windows[0]
        token = json.dumps(self.password)
        window.evaluate_js(f'localStorage.setItem("sambotl.token", {token})')
        window.evaluate_js(f'window.location.href = "/app/{route}"')


def main() -> int:
    bridge = Bridge()
    window = webview.create_window(
        "SamboTL — рабочее место",
        url=str(UI_FILE),
        js_api=bridge,
        width=1000,
        height=720,
        min_size=(720, 520),
        background_color="#0f172a",
    )
    window.events.loaded += bridge.on_loaded
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
