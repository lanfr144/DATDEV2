# Book&Ride - Unit 02 - log shipper MongoDB -> Elasticsearch
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ship_logs.py .
RUN useradd --create-home app
USER app
# healthy = the heartbeat file was touched less than 30 s ago
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os, sys, time; sys.exit(0 if time.time() - os.path.getmtime(os.environ.get('HEARTBEAT_FILE', '/tmp/heartbeat')) < 30 else 1)"
CMD ["python", "ship_logs.py"]
