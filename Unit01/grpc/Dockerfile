# Book&Ride - Unit 01 - gRPC server. The code is GENERATED from the contract
# (books.proto) at build time: change the .proto, rebuild, both sides follow.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GRPC_PORT=50051
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY books.proto server.py client.py ./
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. books.proto
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 50051
# healthcheck: the TCP port accepts connections
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
  CMD python -c "import socket, os; socket.create_connection(('127.0.0.1', int(os.environ['GRPC_PORT'])), 2)"
CMD ["python", "server.py"]
