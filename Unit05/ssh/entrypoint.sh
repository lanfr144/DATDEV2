#!/bin/bash
# Host keys: created at the FIRST start of the container (ssh-keygen -A), so
# every installation has its own; kept in the volume -> the fingerprint the
# client accepted the first time stays the same (no "host key changed" alarm).
set -euo pipefail
mkdir -p /etc/ssh/keys
[ -f /etc/ssh/keys/ssh_host_ed25519_key ] || ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/keys/ssh_host_ed25519_key
# authorized_keys: the PUBLIC key of the student, mounted read-only from the host.
# Copied with strict rights: sshd refuses a file that others can write (StrictModes).
install -o student -m 600 /authorized_keys /home/student/.ssh/authorized_keys
exec /usr/sbin/sshd -D -e        # -D foreground (PID 1), -e logs to stderr = docker logs
