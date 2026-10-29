"""
Book&Ride - Unit 01 - configuration read from the environment.

Every value comes from .env (via docker compose, or exported in the shell):
nothing is hard-coded, especially not the ports and the passwords.
The full configuration management (dev / staging / prod) arrives in Unit 03.
"""
import os
from urllib.parse import quote_plus

SERVICE_NAME = os.getenv("SERVICE_NAME", "books-api")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
API_PORT = int(os.getenv("API_PORT", "8080"))

MONGO_DB = os.getenv("MONGO_DB", "bookandride")


def mongo_url() -> str:
    """MONGO_URL if given, otherwise built from the separate variables.

    The user and the password are URL-encoded (quote_plus): a password that
    contains '@' or ':' would otherwise break the connection string.
    """
    if os.getenv("MONGO_URL"):
        return os.environ["MONGO_URL"]
    user = quote_plus(os.getenv("MONGO_ROOT_USER", "admin"))
    password = quote_plus(os.getenv("MONGO_ROOT_PASSWORD", ""))
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_HOST_PORT", "27017")
    return f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin"
