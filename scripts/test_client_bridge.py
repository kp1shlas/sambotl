"""Verify the portable client's bridge logic against a running server.

Usage:  python scripts/test_client_bridge.py [port]
Assumes a server is already listening (default http://127.0.0.1:8000) with a
tournament whose access password is ``1234``.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from launcher.client import Bridge  # noqa: E402


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8000"
    server = f"127.0.0.1:{port}"

    bridge = Bridge()

    good = bridge.connect(server, "1234")
    print("connect (верный пароль):", good)

    bridge2 = Bridge()
    bad = bridge2.connect(server, "wrong-password")
    print("connect (неверный пароль):", bad)

    bridge3 = Bridge()
    down = bridge3.connect("127.0.0.1:59999", "1234")
    print("connect (сервер недоступен):", down)

    ok = good.get("ok") is True and bad.get("ok") is False and down.get("ok") is False
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
