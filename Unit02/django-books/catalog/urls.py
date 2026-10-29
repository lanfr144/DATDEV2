from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookViewSet, health

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")

urlpatterns = [
    path("health/", health),
    path("", include(router.urls)),     # "/" = browsable API root of DRF
]
