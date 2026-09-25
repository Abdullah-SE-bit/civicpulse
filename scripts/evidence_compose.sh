#!/usr/bin/env bash
# Runs the Compose-level checks against the dev stack and prints a transcript. Every line is real command output.
# Needs docker compose, curl, jq. Exit code is non-zero if any check FAILs. Run from the repo root.
set -uo pipefail

export COMPOSE_FILE=compose.yaml:scripts/evidence.override.yaml
FRONT=http://localhost:8080
BACK=http://localhost:8000
PASS=0; FAIL=0

say()  { printf '\n=== %s\n' "$*"; }
run()  { printf '$ %s\n' "$*"; "$@" 2>&1; }
check() { # check "name" <command...> ; PASS when the command exits 0
  local name=$1; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $name"; PASS=$((PASS+1)); else echo "FAIL  $name"; FAIL=$((FAIL+1)); fi
}
wait_ready() { for _ in $(seq 1 60); do curl -fsS "$BACK/ready" >/dev/null 2>&1 && return 0; sleep 2; done; return 1; }
post() { curl -sS -o /tmp/post.json -w '%{http_code}' -X POST "$BACK/api/complaints" -H 'Content-Type: application/json' \
  -H "X-Forwarded-For: ${2:-198.51.100.1}" -d "{\"text\":\"$1\",\"location\":\"Street 12\"}"; }

say "environment"
run uname -a; run docker --version; run docker compose version

say "1. compose config validates"
[ -f .env ] || cp .env.example .env
check "docker compose config" docker compose config -q
run docker compose config --services

say "2. images build; build context and image facts"
docker compose build --progress=plain 2>&1 | grep -E "transferring context|naming to" | sed 's/^#[0-9]* [0-9.]* //'
run docker image ls --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep -E "REPOSITORY|civicpulse"

say "3. stack up"
run docker compose up -d --quiet-pull
check "backend becomes ready" wait_ready
run docker compose ps

say "4. image contents"
run docker compose exec -T backend id
check "backend runs as non-root" bash -c '[ "$(docker compose exec -T backend id -u | tr -d "\r")" != "0" ]'
run docker compose exec -T frontend id
check "frontend runs as non-root" bash -c '[ "$(docker compose exec -T frontend id -u | tr -d "\r")" != "0" ]'
check "frontend image has no node" bash -c '! docker compose exec -T frontend sh -c "command -v node"'
check "frontend image has no node_modules" bash -c '! docker compose exec -T frontend sh -c "test -d /app/node_modules -o -d /usr/src/app/node_modules"'
run docker compose exec -T frontend ls /usr/share/nginx/html

say "5. frontend and probes"
check "frontend serves the app shell" bash -c "curl -fsS $FRONT/ | grep -q 'id=\"root\"'"
run curl -sS -i "$BACK/health"
run curl -sS -i "$BACK/ready"
check "/health 200" curl -fsS "$BACK/health"
check "/ready 200 (postgres + redis)" curl -fsS "$BACK/ready"
check "/metrics has request counter" bash -c "curl -fsS $BACK/metrics | grep -q http_requests_total"

say "6. create, retrieve, stats cache (through the frontend proxy)"
created=$(curl -fsS -X POST "$FRONT/api/complaints" -H 'Content-Type: application/json' \
  -H 'X-Forwarded-For: 198.51.100.50' -d '{"text":"Burst water main flooding Street 12, water entering ground floors","location":"Street 12"}')
echo "$created" | jq .
ID=$(echo "$created" | jq -r .id)
check "GET complaint back" bash -c "curl -fsS $FRONT/api/complaints/$ID | jq -e '.category'"
run curl -sS -D - -o /dev/null "$FRONT/api/stats" | grep -iE "^HTTP|x-cache"
run curl -sS -D - -o /dev/null "$FRONT/api/stats" | grep -iE "^HTTP|x-cache"
echo '$ curl /api/meta/providers'; curl -sS "$FRONT/api/meta/providers" | jq -c '{active, n_recent: (.recent|length), triage_cache}'

say "7. status transitions and 409"
code=$(curl -sS -o /tmp/t1.json -w '%{http_code}' -X PATCH "$BACK/api/complaints/$ID/status" -H 'Content-Type: application/json' -d '{"status":"in_progress"}')
echo "open -> in_progress: HTTP $code"; check "valid transition 200" test "$code" = 200
code=$(curl -sS -o /tmp/t2.json -w '%{http_code}' -X PATCH "$BACK/api/complaints/$ID/status" -H 'Content-Type: application/json' -d '{"status":"open"}')
echo "in_progress -> open: HTTP $code"; cat /tmp/t2.json; echo
check "invalid transition 409" test "$code" = 409
check "409 names the transition" bash -c "grep -q 'in_progress' /tmp/t2.json && grep -q 'open' /tmp/t2.json"
code=$(curl -sS -o /dev/null -w '%{http_code}' "$BACK/api/complaints/00000000-0000-0000-0000-000000000000")
echo "unknown id: HTTP $code"; check "404 for unknown id" test "$code" = 404
code=$(curl -sS -o /tmp/v.json -w '%{http_code}' -X POST "$BACK/api/complaints" -H 'Content-Type: application/json' -d '{"text":"short","location":"x"}')
echo "invalid body: HTTP $code"; cat /tmp/v.json; echo; check "400 with field errors" test "$code" = 400

say "8. rate limit (per client IP, limit is RATE_LIMIT_PER_MINUTE, default 20)"
ok=0; limited=0; ra=""
for i in $(seq 1 25); do
  c=$(curl -sS -D /tmp/h.txt -o /dev/null -w '%{http_code}' -X POST "$BACK/api/complaints" -H 'Content-Type: application/json' \
      -H 'X-Forwarded-For: 203.0.113.77' -d '{"text":"Streetlight not working near the bus stop","location":"Main Road"}')
  if [ "$c" = 201 ]; then ok=$((ok+1)); elif [ "$c" = 429 ]; then limited=$((limited+1)); ra=$(grep -i '^retry-after' /tmp/h.txt | tr -d '\r'); fi
done
echo "25 requests from one client: $ok x 201, $limited x 429, header: ${ra:-none}"
check "some requests were rate limited" test "$limited" -gt 0
check "429 carries Retry-After" test -n "$ra"
check "a different client is not limited" test "$(post 'Garbage piled up near the market for days' 203.0.113.99)" = 201

say "8b. the limiter cannot be bypassed by a spoofed X-Forwarded-For (through the frontend proxy)"
# nginx APPENDS the real peer to whatever the client sends, so a client that rotates a fake first hop must still be limited.
# This is the check step 8 could not make: it posts straight to the backend. Needs the last-hop fix (PR #46).
docker compose exec -T redis redis-cli flushall >/dev/null
sp_ok=0; sp_lim=0
for i in $(seq 1 30); do
  c=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$FRONT/api/complaints" -H 'Content-Type: application/json'       -H "X-Forwarded-For: 10.9.9.$i" -d '{"text":"Streetlight not working near the bus stop for a week","location":"Main Road"}')
  [ "$c" = 201 ] && sp_ok=$((sp_ok+1)); [ "$c" = 429 ] && sp_lim=$((sp_lim+1))
done
echo "30 POSTs via the proxy with rotating spoofed first hops: $sp_ok x 201, $sp_lim x 429"
echo "limiter keys in redis:"; docker compose exec -T redis redis-cli --scan --pattern 'rl:*' | tr -d '' | sort | head -5
check "spoofed first hops do not evade the limit" test "$sp_lim" -gt 0
check "spoofed hops share one limiter key" bash -c "[ \"$(docker compose exec -T redis redis-cli --scan --pattern 'rl:*' | wc -l)\" -le 2 ]"

say "9. network isolation"
run docker network ls --format '{{.Name}}\t{{.Driver}}\tinternal={{.Internal}}' | grep civicpulse
for n in edge internal; do run docker network inspect "civicpulse_$n" --format '{{.Name}} internal={{.Internal}} members={{range .Containers}}{{.Name}} {{end}}'; done
echo "-- frontend -> postgres (must fail)"; run docker compose exec -T frontend ping -c1 -W2 postgres
check "frontend cannot reach postgres" bash -c '! docker compose exec -T frontend ping -c1 -W2 postgres'
echo "-- frontend -> redis (must fail)"; run docker compose exec -T frontend ping -c1 -W2 redis
check "frontend cannot reach redis" bash -c '! docker compose exec -T frontend ping -c1 -W2 redis'
check "frontend can reach backend" docker compose exec -T frontend wget -qO- -T3 http://backend:8000/health
check "backend can reach postgres:5432" docker compose exec -T backend python -c "import socket;socket.create_connection(('postgres',5432),3)"
check "backend can reach redis:6379" docker compose exec -T backend python -c "import socket;socket.create_connection(('redis',6379),3)"
echo "-- outbound from the internal network (must fail)"
check "wget exists in the postgres image (so the next result is about the network)" docker compose exec -T postgres sh -c "command -v wget"
run docker compose exec -T postgres sh -c "wget -T4 -O- http://example.com"
check "postgres has no outbound route" bash -c '! docker compose exec -T postgres sh -c "wget -q -T4 -O- http://example.com"'
check "backend has outbound route via edge" docker compose exec -T backend python -c "import urllib.request as u;u.urlopen('https://example.com',timeout=6)"

say "10. redis down: readiness and degradation"
run docker compose stop redis
sleep 3
run curl -sS -i "$BACK/ready"
check "/ready is 503 when redis is down" bash -c "[ \"\$(curl -s -o /tmp/r.json -w '%{http_code}' $BACK/ready)\" = 503 ]"
check "503 body names redis" bash -c "grep -q redis /tmp/r.json"
check "/health still 200 with redis down" curl -fsS "$BACK/health"
echo "-- create with redis down (cache misses, limiter fails open)"; echo "HTTP $(post 'Pothole on the main road causing accidents' 192.0.2.10)"
run docker compose start redis
check "ready again after redis returns" wait_ready

say "11. provider failure -> rules fallback (unreachable LLM endpoint, dummy key)"
TRIAGE_PROVIDER=llm LLM_API_KEY=dummy-not-a-real-key LLM_BASE_URL=http://127.0.0.1:9/v1 run docker compose up -d --force-recreate backend
check "backend ready with a broken provider" wait_ready
echo '$ curl /api/meta/providers'; curl -sS "$BACK/api/meta/providers" | jq -c '{active, recent: .recent[0:3]}'
code=$(post 'Sewer overflowing into the street near the school' 192.0.2.20); echo "POST -> HTTP $code"
check "still 201 when the provider fails" test "$code" = 201
echo '$ curl newest complaint'; curl -sS "$BACK/api/complaints?page=1&page_size=1" | jq -c '.items[0]|{triaged_by,category,priority,ai_summary}'
check "triaged_by is rules:fallback" bash -c "curl -fsS '$BACK/api/complaints?page=1&page_size=1' | jq -e '.items[0].triaged_by==\"rules:fallback\"'"
run docker compose logs backend --no-log-prefix | grep -m3 "triage fallback"
run curl -sS "$BACK/metrics" | grep -E "^triage_fallback_total"
run docker compose up -d --force-recreate backend
check "backend back on the default provider" wait_ready

say "12. persistence: down (no -v) then up"
BEFORE=$(curl -fsS "$BACK/api/complaints?page=1&page_size=1" | jq .total); echo "total before: $BEFORE"
run docker compose down
run docker compose up -d --quiet-pull
check "ready after down/up" wait_ready
AFTER=$(curl -fsS "$BACK/api/complaints?page=1&page_size=1" | jq .total); echo "total after: $AFTER"
check "row count preserved" test "$BEFORE" = "$AFTER"
check "the created complaint still exists" bash -c "curl -fsS $BACK/api/complaints/$ID | jq -e '.id'"
run docker volume ls --format '{{.Name}}' | grep civicpulse

say "13. graceful shutdown"
CID=$(docker compose ps -q backend)
echo "-- A. an in-flight request must survive SIGTERM: upload a ~1.2 KB body at 300 B/s (~4 s) and signal 1.5 s in"
jq -n --arg t "$(for _ in $(seq 1 25); do printf 'Drain flooding on the main road near the school. '; done)" '{text:$t,location:"Main Road"}' > /tmp/slow.json
wc -c /tmp/slow.json
( code=$(curl -sS -o /tmp/slow.out -w '%{http_code}' --limit-rate 300 -X POST "$BACK/api/complaints"     -H 'Content-Type: application/json' -H 'X-Forwarded-For: 192.0.2.77' --data-binary @/tmp/slow.json);   echo "$code $(date +%s.%N)" > /tmp/slow.res ) &
SLOWPID=$!
sleep 1.5
T_SIG=$(date +%s.%N); echo "SIGTERM sent at $T_SIG"
run docker compose kill -s SIGTERM backend
EXIT=$(docker wait "$CID"); T_EXIT=$(date +%s.%N); echo "container exit code: $EXIT at $T_EXIT"
wait $SLOWPID 2>/dev/null
read -r SLOW_CODE T_DONE < /tmp/slow.res
echo "in-flight request answered HTTP $SLOW_CODE at $T_DONE"
run docker logs --tail 6 "$CID"
check "in-flight request completed with 201" test "$SLOW_CODE" = 201
check "it completed after SIGTERM was sent (was really in flight)" awk -v a="$T_DONE" -v b="$T_SIG" 'BEGIN{exit !(a>b)}'
check "backend exited 0" test "$EXIT" = 0
run docker compose up -d --quiet-pull backend
check "backend restarts cleanly" wait_ready
check "the in-flight complaint was persisted" bash -c "curl -fsS $BACK/api/complaints/$(jq -r .id /tmp/slow.out) | jq -e '.id'"
echo "-- B. new requests after SIGTERM are refused, not half-served (sequential loop)"
( for _ in $(seq 1 150); do curl -s -o /dev/null -w '%{http_code}
' --max-time 3 "$BACK/api/complaints?page=1&page_size=50" 2>/dev/null; done ) > /tmp/load.txt &
LOADPID=$!
sleep 0.7; run docker compose kill -s SIGTERM backend
docker wait "$(docker compose ps -aq backend)" >/dev/null
wait $LOADPID 2>/dev/null
echo "ordered codes, run-length encoded:"; uniq -c /tmp/load.txt
check "no success after the first failure (failures only at the tail)" awk '$1!="200"{f=1} f&&$1=="200"{bad=1} END{exit bad}' /tmp/load.txt
check "no 5xx" bash -c "! grep -qE '^5' /tmp/load.txt"
run docker compose up -d --quiet-pull backend
check "backend restarts cleanly again" wait_ready

say "summary"
echo "PASS=$PASS FAIL=$FAIL"
docker compose down >/dev/null 2>&1
[ "$FAIL" = 0 ]
