#!/usr/bin/env bash
# =============================================================================
# Unit 04 - self-signed TLS certificate of the gateway (DEVOP2 U11 sheet 20,
# DATOP2 U04 slide 7: public key in the certificate, PRIVATE key stays secret).
#   ./scripts/make_certs.sh          (called by compose.sh when missing)
#   ./scripts/make_certs.sh --force  (new certificate = "rotation")
# Output: gateway/certs/gateway.key (private, git-ignored) + gateway.crt (public)
# In production: a certificate signed by a CA (e.g. Let's Encrypt), renewed
# automatically - same files, same NGINX lines.
# =============================================================================
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/gateway/certs"
mkdir -p "$DIR"
if [ -s "$DIR/gateway.crt" ] && [ "${1:-}" != --force ]; then exit 0; fi
# MSYS_NO_PATHCONV: Git Bash on Windows would rewrite "/CN=..." into a path
MSYS_NO_PATHCONV=1 openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout "$DIR/gateway.key" -out "$DIR/gateway.crt" \
  -subj "/C=LU/O=BookAndRide/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
chmod 644 "$DIR/gateway.key"     # read by NGINX in the container (lab only; prod: 600 + root)
echo "certificate created: $(openssl x509 -in "$DIR/gateway.crt" -noout -subject -enddate | tr '\n' ' ')"
