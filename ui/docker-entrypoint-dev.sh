#!/bin/sh
# Dev stack: node_modules lives on a named Docker volume. Reinstall when
# package.json / package-lock.json change, or when the tree is incomplete
# (e.g. volume predates a new dependency — Vite then fails to resolve imports).
#
# This script runs only on container start. After editing it or adding deps,
# recreate the process: `make dev-ui-restart` (or `docker compose ... restart ui`).
set -e
cd /app/ui
HASH=$( (cat package.json && cat package-lock.json) | md5sum | cut -d" " -f1)
need_ci=false
if [ ! -f node_modules/.deps_hash ] || [ "$(cat node_modules/.deps_hash 2>/dev/null)" != "$HASH" ]; then
  need_ci=true
fi
# Self-heal broken/partial installs (empty dirs / interrupted npm ci), and
# refresh when a new dependency was added but the named volume still has an old tree
# (hash-only detection can miss that if .deps_hash was copied or the volume predates the dep).
critical_deps="react-markdown react-pdf remark-breaks simple-icons"
for pkg in $critical_deps; do
  if [ ! -f "node_modules/$pkg/package.json" ]; then
    need_ci=true
    break
  fi
done
if [ "$need_ci" = true ]; then
  # Volume mount is the node_modules dir itself — rm the tree contents, not the mount.
  rm -rf node_modules/* node_modules/.[!.]* node_modules/..?* 2>/dev/null || true
  npm ci
  echo "$HASH" > node_modules/.deps_hash
fi
# Stale named volumes can miss new deps even when .deps_hash matches; reconcile with package.json.
if ! node scripts/check-node-modules.mjs; then
  echo "docker-entrypoint-dev: reinstalling node_modules (check-node-modules failed)"
  rm -rf node_modules/* node_modules/.[!.]* node_modules/..?* 2>/dev/null || true
  npm ci
  echo "$HASH" > node_modules/.deps_hash
fi
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
