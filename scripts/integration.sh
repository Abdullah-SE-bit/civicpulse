#!/usr/bin/env bash
# End-to-end check against a running dev stack (compose.yaml): wait for /ready, POST a complaint, GET it back,
# assert the category, and check /api/stats goes X-Cache MISS -> HIT. Requires curl and jq.
set -euo pipefail

BACKEND=${BACKEND_URL:-http://localhost:8000}
FRONTEND=${FRONTEND_URL:-http://localhost:8080}

echo "waiting for $BACKEND/ready"
for _ in $(seq 1 60); do
  curl -fsS "$BACKEND/ready" >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS "$BACKEND/ready" >/dev/null

# Go through the frontend's /api proxy, so the nginx route is tested too.
created=$(curl -fsS -X POST "$FRONTEND/api/complaints" -H 'Content-Type: application/json' \
  -d '{"text":"Burst water main flooding Street 12, water entering ground floors","location":"Street 12"}')
id=$(jq -er .id <<<"$created")
fetched=$(curl -fsS "$FRONTEND/api/complaints/$id")
category=$(jq -er .category <<<"$fetched")
case "$category" in water|electricity|sanitation|roads|streetlights|other) ;; *) echo "bad category: $category"; exit 1;; esac
echo "created $id category=$category"

# The POST invalidated the stats cache, so the first read must be a MISS and the second a HIT.
first=$(curl -fsS -D - -o /dev/null "$FRONTEND/api/stats" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-cache"{print $2}')
second=$(curl -fsS -D - -o /dev/null "$FRONTEND/api/stats" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-cache"{print $2}')
[ "$first" = "MISS" ] && [ "$second" = "HIT" ] || { echo "X-Cache expected MISS,HIT got $first,$second"; exit 1; }
echo "integration OK"
