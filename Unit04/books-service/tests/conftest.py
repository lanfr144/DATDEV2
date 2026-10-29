"""
The configuration is read when app.* modules are imported: the test
environment must be set BEFORE (conftest.py is loaded first by pytest).
dev + SQLite file + no MongoDB (MONGO_HOST="" -> logs on stdout only).
"""
import os

os.environ.update({
    "APP_ENV": "dev",
    "DB_URL": "sqlite:///./test.db",
    "DB_PASSWORD": "test-db-password",
    "MONGO_HOST": "",
})
