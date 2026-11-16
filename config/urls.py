"""URL configuration for SamboTL."""
from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import include, path, re_path


def health(request):
    """Health + tournament info — used by the portable client and the SPA."""
    payload = {"status": "ok", "app": "SamboTL", "tournament": None}
    try:
        from apps.tournaments.models import Tournament

        tournament = Tournament.objects.order_by("id").first()
        if tournament is not None:
            payload["tournament"] = {
                "id": tournament.id,
                "name": tournament.name,
                "association": tournament.association,
                "mats": tournament.mats_count,
                "stage": tournament.current_stage,
                "system": tournament.system,
                "audience": tournament.audience,
            }
    except Exception:  # pragma: no cover - never break the health probe
        pass
    return JsonResponse(payload)


def _spa(request, *args, **kwargs):
    """Serve the Vue SPA (index.html) at /app/ and client-side routes."""
    index = Path(settings.BUNDLE_DIR) / "static" / "spa" / "index.html"
    if not index.exists():
        # Fall back to collected static (production/frozen layout).
        index = Path(settings.STATIC_ROOT) / "spa" / "index.html"
    if not index.exists():
        return JsonResponse(
            {"error": "Frontend not built. Run: cd frontend && npm run build"},
            status=503,
        )
    content = index.read_text(encoding="utf-8")
    return HttpResponse(content)


urlpatterns = [
    path("", lambda request: redirect("/app/")),
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("apps.participants.urls")),
    path("api/", include("apps.competition.urls")),
    path("api/", include("apps.core.urls")),
    # Vue SPA — everything under /app/ falls back to index.html.
    path("app/", _spa, name="spa"),
    re_path(r"^app/.*$", _spa),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
