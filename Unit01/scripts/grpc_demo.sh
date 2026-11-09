#!/usr/bin/env bash
# =============================================================================
# Unit 01 - gRPC demo (DATOP2 U01): start the gRPC server (profile "grpc") next
# to the REST API, create a book through REST, read it back through gRPC.
#   ./scripts/grpc_demo.sh            (the stack must run: docker compose up -d --wait)
# =============================================================================
source "$(dirname "$0")/_env.sh"
docker compose --profile grpc up -d --build --wait grpc
ISBN="978-$(date +%s)$((RANDOM % 9))"
curl -s -o /dev/null -w "REST POST /books -> %{http_code}\n" -X POST "http://localhost:${API_HOST_PORT}/books" \
  -H 'Content-Type: application/json' \
  -d "{\"title\":\"gRPC in practice\",\"author\":\"Book&Ride\",\"year\":2026,\"isbn\":\"$ISBN\"}"
docker compose --profile grpc run --rm --no-deps grpc python client.py "Book&Ride" | tee /tmp/grpc_out.txt
grep -q "NOT_FOUND" /tmp/grpc_out.txt && grep -q "INVALID_ARGUMENT" /tmp/grpc_out.txt \
  && echo "OK   gRPC: unary + streaming + status codes" || { echo "FAIL gRPC demo"; exit 1; }
