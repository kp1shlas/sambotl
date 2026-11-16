"""Verify the built SPA is served correctly by Django."""
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
from django.test import Client  # noqa: E402

django.setup()

client = Client()
response = client.get("/app/")
print("SPA /app/:", response.status_code)

html = response.content.decode("utf-8", "ignore")
match = re.search(r'src="([^"]+)"', html)
print("asset ref:", match.group(1) if match else None)

if match:
    asset = client.get(match.group(1))
    print("asset:", asset.status_code)

css_match = re.search(r'href="([^"]+\.css)"', html)
if css_match:
    css = client.get(css_match.group(1))
    print("css:", css.status_code)

health = client.get("/api/health/")
print("health:", health.status_code, health.json().get("tournament", {}).get("name"))

redirect = client.get("/")
print("root redirect:", redirect.status_code, redirect.get("Location"))

deep = client.get("/app/weighing")
print("deep link /app/weighing:", deep.status_code)

for route in ("/app/draw", "/app/referee", "/app/scoreboard", "/app/schedule", "/app/reports"):
    response = client.get(route)
    print(f"deep link {route}:", response.status_code)
