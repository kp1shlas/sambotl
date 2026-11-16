"""SamboTL server launcher.

Entry points:
    SamboTLServer.exe                  -> visual GUI (pywebview)
    SamboTLServer.exe --console        -> headless console mode (auto-browser)
    SamboTLServer.exe --list-tournaments
    SamboTLServer.exe --create-tournament <json>
    SamboTLServer.exe --select <slug>
    SamboTLServer.exe --run <port> [--host H]

The GUI calls the ``--list-tournaments`` / ``--create-tournament`` /
``--select`` sub-modes as one-shot subprocesses, then starts the actual server
with ``--run`` in a background process.
"""
import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Force autobahn's pure-Python WebSocket helpers: the optional native NVX
# extensions do not survive freezing (they need a C source at runtime).
os.environ.setdefault("AUTOBAHN_USE_NVX", "0")

# Ensure the project root is importable both from source and when frozen.
_BASE = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))


def _setup_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("SAMBO_DEBUG", "1")
    import django

    django.setup()


def cmd_list_tournaments() -> int:
    """Print the tournament catalogue as JSON (the GUI parses stdout)."""
    _setup_django()
    from apps.core import registry

    entries = registry.load_index()
    active = registry.get_active() or {}
    active_slug = active.get("slug")
    output = [
        {
            "slug": entry.get("slug"),
            "name": entry.get("name"),
            "system": entry.get("system"),
            "audience": entry.get("audience"),
            "mats": entry.get("mats"),
            "created_at": entry.get("created_at"),
            "active": entry.get("slug") == active_slug,
        }
        for entry in entries
    ]
    print(json.dumps(output, ensure_ascii=False))
    return 0


def cmd_create_tournament(payload_json: str) -> int:
    """Create a tournament (new SQLite file) and its admin superuser."""
    payload = json.loads(payload_json)
    name = (payload.get("name") or "").strip()
    if not name:
        print(json.dumps({"ok": False, "error": "Укажите название турнира"}))
        return 1

    _setup_django()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    system = payload.get("system", "olympic")
    audience = payload.get("audience", "adults")
    mats = int(payload.get("mats", 4))
    password = payload.get("password", "")
    admin_password = payload.get("admin_password", "") or "admin1234"

    try:
        import io

        call_command(
            "new_tournament",
            name,
            system=system,
            audience=audience,
            mats=mats,
            password=password,
            activate=True,
            verbosity=0,
            stdout=io.StringIO(),
        )
    except Exception as exc:  # pragma: no cover - surfaced to the GUI
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    User = get_user_model()
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "", admin_password)

    from apps.core import registry

    active = registry.get_active() or {}
    print(
        json.dumps(
            {"ok": True, "slug": active.get("slug"), "name": name, "admin": "admin"},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_select(slug: str) -> int:
    _setup_django()
    from apps.core import registry

    try:
        registry.set_active(slug)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, "slug": slug}))
    return 0


def cmd_set_access_password(slug: str, password: str) -> int:
    """Change the shared client password for a tournament (and re-hash it)."""
    _setup_django()
    from apps.core.passwords import hash_password
    from apps.tournaments.models import Tournament

    tournament = Tournament.objects.order_by("id").first()
    if tournament is None:
        print(json.dumps({"ok": False, "error": "Активный турнир не найден"}))
        return 1
    tournament.access_password = hash_password(password or "")
    tournament.save(update_fields=["access_password", "updated_at"])
    print(json.dumps({"ok": True, "slug": slug}))
    return 0


def cmd_set_admin_password(slug: str, password: str) -> int:
    """Reset the ``admin`` superuser password."""
    _setup_django()
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="admin", defaults={"is_staff": True, "is_superuser": True}
    )
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password or "admin1234")
    user.save()
    print(json.dumps({"ok": True, "slug": slug}))
    return 0


def cmd_run(port: int, host: str = "0.0.0.0") -> int:
    _setup_django()
    from daphne.endpoints import build_endpoint_description_strings
    from daphne.server import Server
    from config.asgi import application

    endpoints = build_endpoint_description_strings(host=host, port=port)
    server = Server(
        application=application,
        endpoints=endpoints,
        signal_handlers=True,
        verbosity=1,
    )
    server.run()
    return 0


def cmd_console(port: int, host: str, open_browser: bool) -> int:
    """Old headless mode: run daphne in-process and auto-open the browser."""
    _setup_django()
    url = f"http://127.0.0.1:{port}/app/"
    if open_browser:
        threading.Thread(
            target=lambda: (time.sleep(2), webbrowser.open(url)), daemon=True
        ).start()
    print(f"SamboTL сервер: http://<IP-компьютера>:{port}")
    print(f"Экраны:  {url}")
    print(f"Админка: http://127.0.0.1:{port}/admin/")
    return cmd_run(port, host)


def main() -> int:
    args = sys.argv[1:]

    def value_of(flag, default=None):
        if flag in args:
            index = args.index(flag)
            if index + 1 < len(args):
                return args[index + 1]
        return default

    if "--list-tournaments" in args:
        return cmd_list_tournaments()
    if "--create-tournament" in args:
        return cmd_create_tournament(value_of("--create-tournament"))
    if "--select" in args:
        return cmd_select(value_of("--select", ""))
    if "--set-access-password" in args:
        return cmd_set_access_password(
            value_of("--set-access-password", ""), value_of("--value", "")
        )
    if "--set-admin-password" in args:
        return cmd_set_admin_password(
            value_of("--set-admin-password", ""), value_of("--value", "")
        )
    if "--run" in args:
        return cmd_run(int(value_of("--run", "8000")), value_of("--host", "0.0.0.0"))
    if "--console" in args:
        return cmd_console(
            int(value_of("--port", "8000")),
            value_of("--host", "0.0.0.0"),
            "--no-browser" not in args,
        )

    # Default: visual GUI.
    from launcher.server_gui import run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
