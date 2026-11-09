from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BookListCreate, BookViewSet, book_detail, health, hello_world

router = DefaultRouter()
router.register("books", BookViewSet, basename="book")

urlpatterns = [
    path("health/", health),
    path("hello/", hello_world),                       # lab exercise 1 (@api_view)
    path("v1/books/", BookListCreate.as_view()),       # lab exercise 2/4 (generic view)
    path("v1/books/<int:pk>/", book_detail),           # lab exercise 3 (function view)
    path("", include(router.urls)),     # "/" = browsable API root of DRF
]
