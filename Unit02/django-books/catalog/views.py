"""
ModelViewSet = the five REST actions in one class (list, retrieve, create,
update/partial_update, destroy). The router of urls.py creates the URLs:
    /books/          GET (list, paginated)   POST (201)
    /books/{id}/     GET  PUT  PATCH  DELETE (204)
Filters (settings.REST_FRAMEWORK): ?search=  ?ordering=  ?page=  + ?available=
"""
from django.db import connection
from django.http import JsonResponse
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

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


# =============================================================================
# The OTHER ways of writing DRF views, as in the lab (exercises 1 to 4).
# The ModelViewSet above is the shortest; these show what it does for you.
# =============================================================================

@api_view(["GET"])                      # Exercise 1: function view, GET only (other methods -> 405)
def hello_world(request):
    return Response({"message": "Hello, DRF!"})


class BookListCreate(generics.ListCreateAPIView):
    """Exercise 2/4: generic class view = GET (list, paginated, ?search=) + POST (201)."""
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    search_fields = ["title", "author"]


@api_view(["GET", "PUT", "PATCH", "DELETE"])
def book_detail(request, pk):
    """Exercise 3: the detail view written by hand (what ModelViewSet hides).

    PUT   = full replacement: every field required (partial=False) -> 400 if one is missing
    PATCH = partial update: only the fields sent are validated (partial=True)
    DELETE -> 204 without body ; unknown id -> 404
    """
    try:
        book = Book.objects.get(pk=pk)
    except Book.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(BookSerializer(book).data)
    if request.method == "DELETE":
        book.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = BookSerializer(book, data=request.data, partial=request.method == "PATCH")
    serializer.is_valid(raise_exception=True)     # invalid -> 400 with the field errors
    serializer.save()
    return Response(serializer.data)
