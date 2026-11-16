"""Authentication for LAN clients.

The server runs within a closed local network; each tournament has one shared
access password. The portable client asks the operator for that password once,
then attaches it as ``Authorization: Token <password>`` to every request.

Endpoints can also be reached from a logged-in Django admin session (the
organiser's PC), hence :class:`LanAccess` accepts either a valid token or an
authenticated admin user.
"""
from django.contrib.auth.middleware import get_user
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.tournaments.models import Tournament


class AccessTokenAuthentication(BaseAuthentication):
    """Validate a single shared tournament password (PBKDF2 hash)."""

    keyword = "Token"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None

        token = header.removeprefix(self.keyword).strip()
        if not token:
            raise AuthenticationFailed("Неверный пароль доступа")

        tournament = Tournament.objects.order_by("id").first()
        if tournament is None or not tournament.check_password(token):
            raise AuthenticationFailed("Неверный пароль доступа")

        return get_user(request), token


class LanAccess:
    """Allow access with a valid shared password OR an admin session."""

    message = "Требуется пароль доступа к турниру"

    def has_permission(self, request, view):
        if request is None:
            return True
        if getattr(request, "auth", None) is not None:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)