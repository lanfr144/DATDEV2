# Book&Ride - Unit 04 - rentals microservice.
# The version is BAKED into the image: one image tag = one immutable version
#   docker build --build-arg APP_VERSION=1.1.0 -t datdev2/rentals:1.1.0 .
FROM python:3.12-slim
ARG APP_VERSION=1.0.0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} API_PORT=8080
LABEL org.opencontainers.image.version=${APP_VERSION} \
      org.opencontainers.image.title="bookandride-rentals"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=10 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"API_PORT\"]}/rentals/health', timeout=2)"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT}"]
