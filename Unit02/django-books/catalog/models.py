"""ORM model: Django creates the SQL table from this class (python manage.py migrate)."""
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

# same rule as ISBN_PATTERN in api/app/schemas.py
isbn_validator = RegexValidator(r"^97[89]-?\d{1,5}-?\d{1,7}-?\d{1,7}-?\d$", "Invalid ISBN-13")


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    year = models.PositiveIntegerField(validators=[MinValueValidator(1450)])
    isbn = models.CharField(max_length=17, unique=True, validators=[isbn_validator])
    price = models.DecimalField(max_digits=7, decimal_places=2,
                                validators=[MinValueValidator(0.01)])
    tags = models.JSONField(default=list, blank=True)
    available = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.year})"
