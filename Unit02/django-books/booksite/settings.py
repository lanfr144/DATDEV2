"""
Book&Ride - Unit 02 - the same /books resource written with Django REST Framework
(DATOP2 Unit 02c), to compare with the FastAPI service of api/.

Configuration from the environment, as everywhere in this project:
DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DJANGO_DB_PATH, MONGO_*.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# the key signs sessions and CSRF tokens: from .env, never in Git
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-key-for-local-tests-only")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "catalog.middleware.JsonLogMiddleware",    # one JSON log per request -> MongoDB
]

ROOT_URLCONF = "booksite.urls"
WSGI_APPLICATION = "booksite.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,   # templates of the browsable API of DRF
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

# SQLite, like the DATOP2 lab; the file lives in a Docker volume (DJANGO_DB_PATH)
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.getenv("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
}}

REST_FRAMEWORK = {
    # ?page=2 -> {"count", "next", "previous", "results"}
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 5,
    # ?search=dune  and  ?ordering=-year
    "DEFAULT_FILTER_BACKENDS": ["rest_framework.filters.SearchFilter",
                                "rest_framework.filters.OrderingFilter"],
    # no login in this example (FastAPI has none either)
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
