# Book&Ride - Unit 02 - Django REST Framework variant of the books API
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home app && mkdir /data && chown app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=10 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"DJANGO_PORT\"]}/health/', timeout=2)"
# migrate (creates/updates the SQLite tables) then serve with gunicorn
# (runserver is for development only: single-threaded, not hardened)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn booksite.wsgi --bind 0.0.0.0:${DJANGO_PORT} --workers 2 --access-logfile -"]
