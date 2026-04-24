#!/bin/sh
# Dev stack: node_modules lives on a named Docker volume, so new lockfile deps
# are invisible until we reinstall. Sync when package-lock.json changes.
set -e
cd /app/ui
HASH=$(md5sum package-lock.json | awk '{print $1}')
if [ ! -f node_modules/.deps_hash ] || [ "$(cat node_modules/.deps_hash 2>/dev/null)" != "$HASH" ]; then
  npm ci
  echo "$HASH" > node_modules/.deps_hash
fi
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
