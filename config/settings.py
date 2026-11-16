"""
Django settings for SamboTL — a system for running and automating Sambo tournaments.

Deployment model (as agreed with the customer):
  * Offline-first: no external CDNs, all assets are served locally.
  * Windows-only environment. One PC runs the server, the rest connect over LAN.
  * One SQLite file per tournament ("file per tournament" storage model).

The working database file is resolved at startup (see ``_resolve_database_path``).
"""
import json
import os
import sys
from pathlib import Path

from django.urls import reverse_lazy

# ---------------------------------------------------------------------------
# Paths — aware of a PyInstaller "frozen" build.
#
#   * BUNDLE_DIR — read-only files shipped inside the executable
#                  (templates, collected static). ``sys._MEIPASS`` when frozen.
#   * BASE_DIR   — the writable working directory next to the .exe
#                  (data/, tournaments, media, backups).
# ---------------------------------------------------------------------------
FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = BUNDLE_DIR

DATA_DIR = Path(os.environ.get("SAMBO_DATA_DIR") or (BASE_DIR / "data"))
TOURNAMENTS_DIR = DATA_DIR / "tournaments"
MEDIA_DIR = DATA_DIR / "media"
BACKUPS_DIR = DATA_DIR / "backups"
for _dir in (DATA_DIR, TOURNAMENTS_DIR, MEDIA_DIR, BACKUPS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

ACTIVE_TOURNAMENT_FILE = DATA_DIR / "active_tournament.json"
TOURNAMENTS_INDEX_FILE = DATA_DIR / "tournaments.json"


def _resolve_database_path() -> Path:
    """Return the SQLite file used as the *working* tournament database.

    Priority:
      1. ``SAMBO_DB`` environment variable (used by launchers, tooling, tests).
      2. ``data/active_tournament.json`` — written when a tournament is selected.
      3. ``data/tournaments/default.sqlite3`` — fallback for first run.
    """
    env_db = os.environ.get("SAMBO_DB")
    if env_db:
        return Path(env_db).resolve()

    fallback = TOURNAMENTS_DIR / "default.sqlite3"
    try:
        payload = json.loads(ACTIVE_TOURNAMENT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback

    filename = payload.get("db")
    if not filename:
        return fallback
    return (TOURNAMENTS_DIR / filename).resolve()


DATABASE_PATH = _resolve_database_path()

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SAMBO_SECRET_KEY", "dev-insecure-sambo-tl-key-change-me-before-release"
)
# LAN tournaments run with DEBUG on by default so static/media are served
# without an extra web server. Set SAMBO_DEBUG=0 for a "production" run.
DEBUG = os.environ.get("SAMBO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

INSTALLED_APPS = [
    # Django Unfold must be listed before django.contrib.admin.
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "channels",
    # SamboTL applications
    "apps.core",
    "apps.tournaments",
    "apps.participants",
    "apps.competition",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BUNDLE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database — one SQLite file per tournament
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_PATH,
        "OPTIONS": {
            # Helps concurrent access from several LAN clients.
            "timeout": 20,
            "init_command": "PRAGMA journal_mode=WAL;",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Channels — in-memory layer is enough for a single offline server process
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
# Static files are shipped inside the bundle (read-only) and served by WhiteNoise.
STATIC_ROOT = Path(os.environ.get("SAMBO_STATIC_ROOT") or (BUNDLE_DIR / "staticfiles"))
STATICFILES_DIRS = [BUNDLE_DIR / "static"] if (BUNDLE_DIR / "static").exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Compressed (non-manifest) storage works out of the box in a frozen build
    # without requiring a collected manifest file.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = MEDIA_DIR

# ---------------------------------------------------------------------------
# CORS / DRF — open within the LAN, the access password is enforced by the app
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.auth.AccessTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# ---------------------------------------------------------------------------
# Unfold — the polished admin UI (dashboard, live tournament control)
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "SamboTL — Турниры по самбо",
    "SITE_HEADER": "SamboTL",
    "SITE_SUBHEADER": "Система проведения турниров по самбо",
    "SITE_URL": "/admin/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Турнир",
                "separator": True,
                "items": [
                    {
                        "title": "Турниры и настройки",
                        "icon": "emoji_events",
                        "link": reverse_lazy("admin:tournaments_tournament_changelist"),
                    },
                    {
                        "title": "Этапы",
                        "icon": "flag",
                        "link": reverse_lazy("admin:tournaments_stage_changelist"),
                    },
                ],
            },
            {
                "title": "Участники",
                "separator": True,
                "items": [
                    {
                        "title": "Участники",
                        "icon": "groups",
                        "link": reverse_lazy("admin:participants_participant_changelist"),
                    },
                    {
                        "title": "Взвешивание",
                        "icon": "scale",
                        "link": reverse_lazy("admin:participants_weighin_changelist"),
                    },
                    {
                        "title": "Клубы и регионы",
                        "icon": "location_city",
                        "link": reverse_lazy("admin:participants_club_changelist"),
                    },
                ],
            },
            {
                "title": "Соревнования",
                "separator": True,
                "items": [
                    {
                        "title": "Возрастные группы",
                        "icon": "child_care",
                        "link": reverse_lazy("admin:competition_agegroup_changelist"),
                    },
                    {
                        "title": "Весовые категории",
                        "icon": "fitness_center",
                        "link": reverse_lazy(
                            "admin:competition_weightcategory_changelist"
                        ),
                    },
                    {
                        "title": "Сетки",
                        "icon": "account_tree",
                        "link": reverse_lazy("admin:competition_bracket_changelist"),
                    },
                    {
                        "title": "Схватки",
                        "icon": "sports_martial_arts",
                        "link": reverse_lazy("admin:competition_bout_changelist"),
                    },
                    {
                        "title": "Ковры",
                        "icon": "grid_view",
                        "link": reverse_lazy("admin:competition_mat_changelist"),
                    },
                    {
                        "title": "Судьи",
                        "icon": "gavel",
                        "link": reverse_lazy("admin:competition_referee_changelist"),
                    },
                ],
            },
        ],
    },
}


