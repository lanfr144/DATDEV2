"""
DRF serializer = the Django equivalent of the Pydantic model BookIn.

    Pydantic (FastAPI)                 DRF (Django)
    Field(ge=1450)                     model validators (MinValueValidator)
    @field_validator("year")           validate_year()
    invalid -> 422                     invalid -> 400 Bad Request
    unique ISBN -> 409 (our code)      unique ISBN -> 400 (UniqueValidator, automatic)
"""
from datetime import date

from rest_framework import serializers

from .models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author", "year", "isbn", "price", "tags", "available"]

    def validate_year(self, value):
        if value > date.today().year:
            raise serializers.ValidationError("The publication year cannot be in the future")
        return value

    def validate_tags(self, value):
        if not isinstance(value, list) or len(value) > 5:
            raise serializers.ValidationError("At most 5 tags")
        return sorted({str(t).strip().lower() for t in value})
