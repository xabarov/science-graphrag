#!/bin/sh
# Dev stack: node_modules lives on a named Docker volume. Reinstall when
# package.json / package-lock.json change, or when the tree is incomplete
# (e.g. volume predates a new dependency — Vite then fails to resolve imports).
set -e
cd /app/ui
HASH=$( (cat package.json && cat package-lock.json) | md5sum | cut -d" " -f1)
need_ci=false
if [ ! -f node_modules/.deps_hash ] || [ "$(cat node_modules/.deps_hash 2>/dev/null)" != "$HASH" ]; then
  need_ci=true
fi
# Self-heal broken/partial installs (empty dirs / interrupted npm ci).
if [ ! -f node_modules/react-markdown/package.json ] || [ ! -f node_modules/react-pdf/package.json ]; then
  need_ci=true
fi
if [ "$need_ci" = true ]; then
  # Volume mount is the node_modules dir itself — rm the tree contents, not the mount.
  rm -rf node_modules/* node_modules/.[!.]* node_modules/..?* 2>/dev/null || true
  npm ci
  echo "$HASH" > node_modules/.deps_hash
fi
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
