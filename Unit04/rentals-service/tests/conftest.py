import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"   # set BEFORE importing the app
os.environ.pop("MONGO_HOST", None)                  # logs on stdout only
