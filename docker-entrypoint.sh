#!/bin/sh
set -eu
if [ -f /app/assets/ascii-logo.txt ]; then
  cat /app/assets/ascii-logo.txt
  printf '\n'
fi
exec "$@"
