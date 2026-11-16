"""Participant API routes (mounted under ``/api/``)."""
from rest_framework.routers import DefaultRouter

from .views import ParticipantViewSet, WeighInViewSet

router = DefaultRouter()
router.register("participants", ParticipantViewSet, basename="participant")
router.register("weigh-ins", WeighInViewSet, basename="weigh-in")

urlpatterns = router.urls
