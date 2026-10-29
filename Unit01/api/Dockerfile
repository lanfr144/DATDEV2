# Book&Ride - Unit 01 - books API image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
# dependencies first: this layer stays in cache while only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# never run as root inside the container
RUN useradd --create-home app
USER app

# API_PORT comes from .env (docker compose passes it to the container)
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"API_PORT\"]}/health', timeout=2)"

# sh -c: needed so that ${API_PORT} is replaced at start-up
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}"]
