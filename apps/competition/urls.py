"""Competition API routes (mounted under ``/api/``)."""
from rest_framework.routers import DefaultRouter

from .views import BoutViewSet, BracketViewSet, MatViewSet

router = DefaultRouter()
router.register("brackets", BracketViewSet, basename="bracket")
router.register("mats", MatViewSet, basename="mat")
router.register("bouts", BoutViewSet, basename="bout")

urlpatterns = router.urls