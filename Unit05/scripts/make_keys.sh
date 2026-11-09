#!/usr/bin/env bash
# =============================================================================
# Unit 05 - the two key pairs of the Unit (git-ignored, one per installation)
#   keys/student_ed25519(.pub)  SSH key pair of the user (sheet 23: "SSH-Schlüsselpaare")
#   certs/web.key + web.crt     self-signed X.509 certificate of Apache (sheet 20)
# The PRIVATE parts never leave this machine; only web.crt and the .pub are shared.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p keys certs
[ -f keys/student_ed25519 ] || ssh-keygen -q -t ed25519 -N '' -C "student@bookandride" -f keys/student_ed25519
# sheet 20 does it in 3 steps: private key (genpkey) -> CSR (req -new) -> certificate (x509 -req)
if [ ! -f certs/web.crt ]; then
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out certs/web.key 2>/dev/null
  MSYS_NO_PATHCONV=1 openssl req -new -key certs/web.key -out certs/web.csr -subj "/C=LU/O=BookAndRide/CN=localhost"
  printf 'subjectAltName=DNS:localhost,IP:127.0.0.1\n' > certs/san.ext
  openssl x509 -req -in certs/web.csr -signkey certs/web.key -days 365 -extfile certs/san.ext -out certs/web.crt 2>/dev/null
  chmod 644 certs/web.key     # read by Apache in the container (lab only)
fi
echo "SSH key:     $(ssh-keygen -lf keys/student_ed25519.pub)"
echo "certificate: $(openssl x509 -in certs/web.crt -noout -subject -enddate | tr '\n' ' ')"
