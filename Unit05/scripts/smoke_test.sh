#!/usr/bin/env bash
# =============================================================================
# Unit 05 - end-to-end test (docker compose up -d --build --wait). Exit 1 on failure.
#   HTTPS + redirect (U11 sheets 20-22) · SSH by key, password refused, SFTP (19, 23)
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
fail=0
check() { if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

# ---------- Apache ----------
check "HTTP :${HTTP_HOST_PORT} -> 301"            301 "$(code "http://localhost:${HTTP_HOST_PORT}/")"
check "redirect target is https://...:${HTTPS_HOST_PORT}/" "https://localhost:${HTTPS_HOST_PORT}/" \
  "$(curl -s -o /dev/null -w '%{redirect_url}' "http://localhost:${HTTP_HOST_PORT}/")"
check "HTTPS with our certificate"                200 "$(code --cacert certs/web.crt "https://localhost:${HTTPS_HOST_PORT}/")"
check "HTTPS page = site test"                    yes "$(curl -s --cacert certs/web.crt "https://localhost:${HTTPS_HOST_PORT}/" | grep -q 'Test' && echo yes || echo no)"
check "unknown CA refused (like the browser)"     000 "$(code "https://localhost:${HTTPS_HOST_PORT}/")"
check "HSTS header"                               yes "$(curl -s -D - -o /dev/null --cacert certs/web.crt "https://localhost:${HTTPS_HOST_PORT}/" | grep -qi '^strict-transport-security' && echo yes || echo no)"
check "port 90 = site temporary, plain HTTP"      yes "$(curl -s "http://localhost:${TEMPORARY_HOST_PORT}/" | grep -q 'Temporary' && echo yes || echo no)"

# ---------- SSH / SFTP ----------
# ssh refuses a private key readable by others; on a Windows drive (/mnt/c) the
# rights cannot be set -> use a private copy in /tmp with mode 600.
KEY=$(mktemp); cp keys/student_ed25519 "$KEY"; chmod 600 "$KEY"
KNOWN=$(mktemp)
SSH_OPTS=(-p "$SSH_HOST_PORT" -o UserKnownHostsFile="$KNOWN" -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=5)
check "ssh with the key"                          student "$(ssh "${SSH_OPTS[@]}" -i "$KEY" student@127.0.0.1 whoami 2>/dev/null)"
# the server lists the methods it still accepts: "password" must not be there
check "server offers publickey only"              publickey "$(ssh -v "${SSH_OPTS[@]}" -o PreferredAuthentications=none student@127.0.0.1 true 2>&1 | sed -n 's/.*Authentications that can continue: //p' | head -1 | tr -d '\r ')"
check "ssh as root -> refused"                    refused "$(ssh "${SSH_OPTS[@]}" -i "$KEY" root@127.0.0.1 true 2>/dev/null && echo accepted || echo refused)"
echo "Book&Ride SFTP test $(date -u +%FT%TZ)" > /tmp/sftp_test.txt
# batch mode (-b): sftp stops and exits 1 at the first failed command
printf 'put /tmp/sftp_test.txt upload/sftp_test.txt\nget upload/sftp_test.txt /tmp/sftp_back.txt\n' > /tmp/sftp_batch.txt
sftp -P "$SSH_HOST_PORT" -o UserKnownHostsFile="$KNOWN" -o BatchMode=yes -i "$KEY" -b /tmp/sftp_batch.txt student@127.0.0.1
check "sftp put + get, same content"            yes "$(cmp -s /tmp/sftp_test.txt /tmp/sftp_back.txt && echo yes || echo no)"
check "the file is on the server"                 yes "$(docker compose exec -T ssh cat /home/student/upload/sftp_test.txt | grep -q 'SFTP test' && echo yes || echo no)"
echo "host key fingerprint accepted: $(ssh-keygen -lf "$KNOWN" | awk '{print $2}' | head -1)"
rm -f "$KEY" "$KNOWN" /tmp/sftp_test.txt /tmp/sftp_back.txt /tmp/sftp_batch.txt
exit $fail
