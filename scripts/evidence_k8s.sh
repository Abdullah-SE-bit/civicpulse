#!/usr/bin/env bash
# Cluster-level checks against a kind cluster that already has ingress-nginx, metrics-server and the dev overlay applied.
# Output is a transcript of real command output; artifacts go to ./out. Needs kubectl, curl, jq, k6, python3+matplotlib.
# Run from the repo root. Env: HIGH_RPS (default 120), HOLD (default 240s).
set -uo pipefail

NS=civicpulse
HOST=civicpulse.localtest.me
RES="--resolve $HOST:80:127.0.0.1"
PASS=0; FAIL=0
mkdir -p out

say()  { printf '\n=== %s\n' "$*"; }
run()  { printf '$ %s\n' "$*"; "$@" 2>&1; }
check() { local name=$1; shift; if "$@" >/dev/null 2>&1; then echo "PASS  $name"; PASS=$((PASS+1)); else echo "FAIL  $name"; FAIL=$((FAIL+1)); fi; }
k() { kubectl -n "$NS" "$@"; }
ing() { curl -sS $RES "$@"; }
count() { ing "http://$HOST/api/complaints?page=1&page_size=1" | jq -r .total; }
cleanup() { [ -n "${PF_PID:-}" ] && kill "$PF_PID" 2>/dev/null; [ -n "${WATCH_PID:-}" ] && kill "$WATCH_PID" 2>/dev/null; [ -n "${SAMPLER_PID:-}" ] && kill "$SAMPLER_PID" 2>/dev/null; }
trap cleanup EXIT

say "environment"
run kubectl version
run kubectl get nodes -o wide
run kind version

say "1. what is deployed"
run kubectl get deployment -A | grep -E "NAMESPACE|metrics|ingress|civicpulse|backend|frontend|redis"
run k get all,ingress,cm,pvc,hpa,pdb -o wide
echo "-- secrets (names only, never values)"; run k get secret
echo "-- replicas per workload"; run k get deploy,statefulset -o custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas
echo "-- backend probes, rollout strategy and resources (from the live object)"
k get deploy backend -o json | jq '.spec.template.spec.containers[0] | {startupProbe, livenessProbe, readinessProbe, resources}' | jq -c '.'
k get deploy backend -o json | jq -c '{strategy: .spec.strategy, terminationGracePeriodSeconds: .spec.template.spec.terminationGracePeriodSeconds, preStop: .spec.template.spec.containers[0].lifecycle}'
echo "-- service types"; run k get svc -o custom-columns=NAME:.metadata.name,TYPE:.spec.type,PORT:.spec.ports[0].port
check "all four services are ClusterIP" bash -c "[ \"\$(kubectl -n $NS get svc -o json | jq '[.items[]|select(.spec.type!=\"ClusterIP\")]|length')\" = 0 ]"
check "postgres is a StatefulSet" k get statefulset postgres
check "postgres has a bound PVC" bash -c "kubectl -n $NS get pvc | grep -q 'pgdata-postgres-0.*Bound'"
check "redis has a bound PVC" bash -c "kubectl -n $NS get pvc | grep -q 'redis-data.*Bound'"
check "every container sets cpu+memory requests and limits" bash -c "kubectl -n $NS get pods -o json | jq -e '[.items[].spec.containers[]|select(.resources.requests.cpu==null or .resources.requests.memory==null or .resources.limits.cpu==null or .resources.limits.memory==null)]|length==0'"
check "backend and frontend have >= 2 ready replicas" bash -c "[ \"\$(kubectl -n $NS get deploy backend -o jsonpath='{.status.readyReplicas}')\" -ge 2 ] && [ \"\$(kubectl -n $NS get deploy frontend -o jsonpath='{.status.readyReplicas}')\" -ge 2 ]"

say "2. metrics-server and kubectl top"
for _ in $(seq 1 30); do kubectl top nodes >/dev/null 2>&1 && break; sleep 5; done
run kubectl top nodes
run kubectl top pods -n "$NS"
check "kubectl top pods works" kubectl top pods -n "$NS"
run k get hpa backend

say "3. behaviour through the Ingress (single host)"
check "frontend served on /" bash -c "curl -fsS $RES http://$HOST/ | grep -q 'id=\"root\"'"
created=$(ing -X POST "http://$HOST/api/complaints" -H 'Content-Type: application/json' -H 'X-Forwarded-For: 198.51.100.50' \
  -d '{"text":"Burst water main flooding Street 12, water entering ground floors","location":"Street 12"}')
echo "$created" | jq -c '{id,category,priority,status,triaged_by}'
ID=$(echo "$created" | jq -r .id)
check "POST /api/complaints -> 201 shape" bash -c "echo '$created' | jq -e '.id and .status==\"open\"'"
check "GET /api/complaints/{id}" bash -c "curl -fsS $RES http://$HOST/api/complaints/$ID | jq -e '.id'"
echo "-- stats cache"; ing -s -D - -o /dev/null "http://$HOST/api/stats" | grep -iE "^HTTP|x-cache"; ing -s -D - -o /dev/null "http://$HOST/api/stats" | grep -iE "^HTTP|x-cache"
code=$(ing -o /dev/null -w '%{http_code}' -X PATCH "http://$HOST/api/complaints/$ID/status" -H 'Content-Type: application/json' -d '{"status":"in_progress"}'); echo "open -> in_progress: HTTP $code"
check "valid transition 200" test "$code" = 200
code=$(ing -o /tmp/t2.json -w '%{http_code}' -X PATCH "http://$HOST/api/complaints/$ID/status" -H 'Content-Type: application/json' -d '{"status":"open"}'); echo "in_progress -> open: HTTP $code"; cat /tmp/t2.json; echo
check "invalid transition 409" test "$code" = 409
echo "-- probes from inside the cluster (port-forward to one backend pod)"
POD=$(k get pod -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl -n "$NS" port-forward "pod/$POD" 18000:8000 >/dev/null 2>&1 & PF_PID=$!
sleep 3
run curl -sS -i http://127.0.0.1:18000/health
run curl -sS -i http://127.0.0.1:18000/ready
check "/health 200" curl -fsS http://127.0.0.1:18000/health
check "/ready 200 (postgres + redis reachable from the pod)" curl -fsS http://127.0.0.1:18000/ready
echo "-- init container that ran migrations + seed"; run k logs "$POD" -c migrate

say "4. postgres pod deleted: rows must survive"
BEFORE=$(count); echo "rows before: $BEFORE"
run k delete pod postgres-0
run k wait --for=condition=ready pod/postgres-0 --timeout=180s
for _ in $(seq 1 30); do curl -fsS http://127.0.0.1:18000/ready >/dev/null 2>&1 && break; sleep 2; done
AFTER=$(count); echo "rows after: $AFTER"
check "row count preserved across postgres pod deletion" test "$BEFORE" = "$AFTER"
check "the created complaint still exists" bash -c "curl -fsS $RES http://$HOST/api/complaints/$ID | jq -e '.id'"

say "5. redis down: readiness and liveness are different decisions"
run k scale deploy/redis --replicas=0
sleep 25
run curl -sS -i http://127.0.0.1:18000/ready
check "/ready is 503 naming redis" bash -c "[ \"\$(curl -s -o /tmp/r.json -w '%{http_code}' http://127.0.0.1:18000/ready)\" = 503 ] && grep -q redis /tmp/r.json"
check "/health still 200 (liveness independent)" curl -fsS http://127.0.0.1:18000/health
echo "-- backend endpoints (pods failing readiness leave the Service)"; run k get endpoints backend
run k get pods -l app=backend
echo "-- restarts stay 0 (liveness did not kill them)"; k get pods -l app=backend -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount
check "no backend restarts caused by redis being down" bash -c "[ \"\$(kubectl -n $NS get pods -l app=backend -o json | jq '[.items[].status.containerStatuses[0].restartCount]|add')\" = 0 ]"
run k scale deploy/redis --replicas=1
run k rollout status deploy/redis --timeout=120s
for _ in $(seq 1 40); do curl -fsS http://127.0.0.1:18000/ready >/dev/null 2>&1 && break; sleep 3; done
check "ready again after redis returns" curl -fsS http://127.0.0.1:18000/ready

run_load() { # run_load <label>: one k6 run with a 2 s timeline of HPA + Deployment state, chart and lag numbers in out/<label>/
  local label=$1 dir=out/$1
  mkdir -p "$dir"
  kubectl -n "$NS" get hpa backend -w > "$dir/hpa-watch.txt" 2>&1 & WATCH_PID=$!
  echo "epoch,current,desired,ready,cpu_pct,spec" > "$dir/timeline.csv"
  ( while true; do
      e=$(date +%s)
      h=$(kubectl -n "$NS" get hpa backend -o jsonpath='{.status.currentReplicas},{.status.desiredReplicas},{.status.currentMetrics[0].resource.current.averageUtilization}' 2>/dev/null)
      d=$(kubectl -n "$NS" get deploy backend -o jsonpath='{.status.readyReplicas},{.spec.replicas}' 2>/dev/null)
      IFS=, read -r cur des cpu <<<"$h"; IFS=, read -r rdy spec <<<"$d"
      echo "$e,${cur:-0},${des:-0},${rdy:-0},${cpu:-},${spec:-0}" >> "$dir/timeline.csv"
      sleep 2
    done ) & SAMPLER_PID=$!
  sleep 10
  echo "k6 start: $(date -u +%FT%TZ) HIGH_RPS=${HIGH_RPS:-120} HOLD=${HOLD:-240s}"
  HIGH_RPS=${HIGH_RPS:-120} HOLD=${HOLD:-240s} k6 run --out csv="$dir/k6-full.csv" --summary-export "$dir/k6-summary.json" load/k6-script.js 2>&1     | grep -vE "^s*$|^(running|hpa_probe)" | tail -32
  echo "k6 end:   $(date -u +%FT%TZ)"
  sleep 20
  kill "$SAMPLER_PID" "$WATCH_PID" 2>/dev/null; SAMPLER_PID=; WATCH_PID=
  grep -E "^(metric_name|http_reqs)," "$dir/k6-full.csv" > "$dir/k6.csv"; rm -f "$dir/k6-full.csv"
  echo "-- kubectl get hpa -w (captured; it prints a row when a value changes)"; cat "$dir/hpa-watch.txt"
  echo "-- HPA events"; k describe hpa backend | sed -n '/Events:/,$p'
  run kubectl top pods -n "$NS"
  ( cd "$dir" && python3 ../../scripts/plot_hpa.py ) 2>&1
  check "$label: chart produced from measured data" test -s "$dir/hpa-replicas-vs-load.png"
}

say "6. HPA under load, run 1 (initial requests; k6 open model; cluster + k6 share one runner)"
echo "runner: $(nproc) vCPU, $(free -m | awk '/Mem:/{print $2}') MB RAM"
run k get hpa backend -o yaml
echo "backend resources before: $(k get deploy backend -o jsonpath='{.spec.template.spec.containers[0].resources}')"
run_load run1

say "7. VPA recommendation (recommender mode, updateMode Off)"
if kubectl get crd verticalpodautoscalers.autoscaling.k8s.io >/dev/null 2>&1; then
  run kubectl apply -f k8s/optional/vpa.yaml
  echo "(waiting for the recommender)"
  for _ in $(seq 1 30); do k get vpa backend-vpa -o jsonpath='{.status.recommendation}' 2>/dev/null | grep -q target && break; sleep 20; done
  run k describe vpa backend-vpa
  echo "-- requests we guessed in k8s/base/backend.yaml:"; k get deploy backend -o jsonpath='{.spec.template.spec.containers[0].resources}'; echo
  TARGET_CPU=$(k get vpa backend-vpa -o json | jq -r '.status.recommendation.containerRecommendations[0].target.cpu // empty')
  if [ -n "$TARGET_CPU" ]; then
    say "8. apply the recommended CPU request, reset replicas, run the load again"
    echo "VPA target cpu = $TARGET_CPU (memory is not changed: see the write-up)"
    run k set resources deploy/backend -c backend --requests=cpu="$TARGET_CPU"
    run k scale deploy/backend --replicas=2
    run k rollout status deploy/backend --timeout=240s
    sleep 45
    echo "backend resources now: $(k get deploy backend -o jsonpath='{.spec.template.spec.containers[0].resources}')"
    run_load run2
    echo "-- lag numbers, run 1 vs run 2"; for r in run1 run2; do echo "[$r]"; cat out/$r/lag.txt; done
  fi
else
  echo "VPA CRD not installed on this cluster; skipped (no recommendation exists, none is claimed)"
fi

say "summary"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = 0 ]
