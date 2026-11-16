"""Verify the server panel bridge logic without opening a window.

Runs: list tournaments, create a temporary tournament, read credentials,
change passwords, then delete the temporary tournament.

Usage:  python scripts/test_server_gui.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from launcher.server_gui import ServerBridge, _load_settings  # noqa: E402

TEST_NAME = "Тест панели сервера"
TEST_SLUG = "test-paneli-servera"


def main() -> int:
    bridge = ServerBridge()

    print("1) Список турниров:", len(bridge.list_tournaments()))

    result = bridge.create_tournament(
        TEST_NAME, "olympic", "mixed", 2, "testpass", "testadmin"
    )
    print("2) Создание турнира:", result)
    if not result.get("ok"):
        return 1

    creds = bridge.active_credentials()
    print("3) Пароли активного турнира:", creds)
    ok_creds = (
        creds.get("access_password") == "testpass"
        and creds.get("admin_password") == "testadmin"
    )

    changed = bridge.set_access_password(TEST_SLUG, "newpass")
    print("4) Смена пароля экранов:", changed)
    creds2 = bridge.credentials_for(TEST_SLUG)
    ok_change = creds2.get("access_password") == "newpass"

    # Restore the previously active tournament.
    restore = bridge.select_tournament("kubok-moskvy-2026")
    print("5) Возврат на прежний турнир:", restore)

    # Clean up the temporary tournament entry and its file.
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from apps.core import registry

    registry.delete_entry(TEST_SLUG, remove_file=True)
    settings = _load_settings()
    settings.pop(TEST_SLUG, None)
    from launcher.server_gui import _save_settings

    _save_settings(settings)

    print("RESULT:", "PASS" if (ok_creds and ok_change) else "FAIL")
    return 0 if (ok_creds and ok_change) else 1


if __name__ == "__main__":
    raise SystemExit(main())
