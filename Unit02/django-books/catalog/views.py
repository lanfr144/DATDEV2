"""
ModelViewSet = the five REST actions in one class (list, retrieve, create,
update/partial_update, destroy). The router of urls.py creates the URLs:
    /books/          GET (list, paginated)   POST (201)
    /books/{id}/     GET  PUT  PATCH  DELETE (204)
Filters (settings.REST_FRAMEWORK): ?search=  ?ordering=  ?page=  + ?available=
"""
from django.db import connection
from django.http import JsonResponse
from rest_framework import viewsets

from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    search_fields = ["title", "author"]             # ?search=herbert
    ordering_fields = ["title", "year", "price"]    # ?ordering=-year

    def get_queryset(self):
        queryset = Book.objects.all()
        available = self.request.query_params.get("available")
        if available in ("true", "false"):
            queryset = queryset.filter(available=(available == "true"))
        return queryset


def health(request):
    """Docker healthcheck: 200 if the SQLite database answers."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok", "service": "books-django"})
