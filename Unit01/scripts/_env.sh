#!/usr/bin/env bash
# Loads ../.env into the shell (shared by the scripts of this folder).
set -euo pipefail
UNIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$UNIT_DIR"
[ -f .env ] || { echo "No .env: run  cp .env.example .env  and set the passwords"; exit 1; }
set -a; . ./.env; set +a
