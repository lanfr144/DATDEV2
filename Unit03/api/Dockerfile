# Book&Ride - Unit 03 - monolith image. The SAME image runs in dev, staging and
# prod ("build once, deploy many"): only APP_ENV and the secrets change.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# config/config.yaml (no secret) is part of the image; config.local.yaml is not
# (excluded by .dockerignore): personal overrides never reach an image
COPY . .
RUN useradd --create-home app && chown -R app /app
USER app
ENV API_PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"API_PORT\"]}/health', timeout=2)"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}"]
