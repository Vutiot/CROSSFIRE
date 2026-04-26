#!/usr/bin/env bash
# Launch the v2 KG viewer (Sigma.js + WebGL).
# Requires `npm install && npm run build` to have been run once in
# tools/kg_viewer_v2/.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DIST="$HERE/tools/kg_viewer_v2/dist"
if [ ! -d "$DIST" ]; then
  echo "tools/kg_viewer_v2/dist/ not found — building first…"
  (cd "$HERE/tools/kg_viewer_v2" && npm install --silent && npm run build)
fi
exec python "$HERE/tools/kg_viewer_v2/serve.py" "$HERE/data/datasets" "$@"
