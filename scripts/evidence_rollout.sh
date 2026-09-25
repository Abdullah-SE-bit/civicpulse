#!/usr/bin/env bash
# Rolling update under load, then both rollback mechanisms, on a kind cluster that already has ingress-nginx and the
# dev overlay applied (no metrics-server, so the HPA cannot change replica counts and confound the rollout).
# The "new" image is the SAME image re-tagged (dev-v2): this measures rollout mechanics, not a code change.
# Needs kubectl, k6, curl, jq, kustomize. Run from the repo root. Output is a real transcript.
set -uo pipefail
NS=civicpulse
IMG=ghcr.io/abdullah-se-bit/civicpulse-backend
PASS=0; FAIL=0
mkdir -p out
say()  { printf '\n=== %s\n' "$*"; }
run()  { printf '$ %s\n' "$*"; "$@" 2>&1; }
check() { local name=$1; shift; if "$@" >/dev/null 2>&1; then echo "PASS  $name"; PASS=$((PASS+1)); else echo "FAIL  $name"; FAIL=$((FAIL+1)); fi; }
k() { kubectl -n "$NS" "$@"; }
img() { k get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}'; }
stamp() { date -u +%T; }

say "environment"
run kubectl version --short 2>/dev/null || run kubectl version
say "0. starting state"
run k get deploy backend -o wide
echo "strategy: $(k get deploy backend -o jsonpath='{.spec.strategy}')"
echo "terminationGracePeriodSeconds: $(k get deploy backend -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'), preStop: $(k get deploy backend -o jsonpath='{.spec.template.spec.containers[0].lifecycle.preStop}')"
echo "image now: $(img)"
check "starts on the :dev tag" bash -c "[ \"\$(kubectl -n $NS get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}')\" = $IMG:dev ]"
kubectl -n "$NS" get pods -l app=backend -w > out/backend-pods-watch.txt 2>&1 & WPID=$!
trap 'kill $WPID 2>/dev/null; kill $KPID 2>/dev/null' EXIT

say "1. start k6: 25 req/s for 300 s through the Ingress"
DURATION=300s RPS=25 k6 run --summary-export out/k6-summary.json load/k6-rollout.js > out/k6-output.txt 2>&1 & KPID=$!
echo "k6 started $(stamp)"; sleep 20

say "2. rolling update: kubectl set image (same image, new tag dev-v2)"
echo "t=$(stamp)"; run k set image deployment/backend backend=$IMG:dev-v2
run k rollout status deployment/backend --timeout=240s
echo "t=$(stamp) image now: $(img)"; run k get rs -l app=backend
check "rollout switched the image to dev-v2" bash -c "[ \"\$(kubectl -n $NS get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}')\" = $IMG:dev-v2 ]"
sleep 15

say "3. rollback mechanism 1: kubectl rollout undo"
echo "t=$(stamp)"; run k rollout history deployment/backend
run k rollout undo deployment/backend
run k rollout status deployment/backend --timeout=240s
echo "t=$(stamp) image now: $(img)"
check "undo restored the :dev tag" bash -c "[ \"\$(kubectl -n $NS get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}')\" = $IMG:dev ]"
sleep 15

say "4. rollback mechanism 2: re-apply the overlay with an image tag (declarative)"
rm -rf /tmp/k8s-copy; cp -r k8s /tmp/k8s-copy; cd /tmp/k8s-copy/overlays/dev
echo "-- roll FORWARD by applying the overlay pinned to dev-v2 (t=$(stamp))"
kustomize edit set image $IMG=$IMG:dev-v2
run bash -c "kustomize build . | kubectl apply -f -"
run k rollout status deployment/backend --timeout=240s; echo "image now: $(img)"
sleep 10
echo "-- roll BACK by applying the overlay pinned to the previous tag dev (t=$(stamp))"
kustomize edit set image $IMG=$IMG:dev
run bash -c "kustomize build . | kubectl apply -f -"
run k rollout status deployment/backend --timeout=240s; echo "image now: $(img)"
cd - >/dev/null
check "declarative re-apply restored :dev" bash -c "[ \"\$(kubectl -n $NS get deploy backend -o jsonpath='{.spec.template.spec.containers[0].image}')\" = $IMG:dev ]"

say "5. wait for k6 to finish and read its measured result"
wait $KPID 2>/dev/null
kill $WPID 2>/dev/null
tail -25 out/k6-output.txt | grep -vE "^\s*$"
REQS=$(jq '.metrics.http_reqs.count' out/k6-summary.json); FAILED=$(jq '.metrics.http_req_failed.passes' out/k6-summary.json)
CHK=$(jq '.metrics.checks.fails' out/k6-summary.json 2>/dev/null || echo "?")
echo "requests=$REQS failed(http_req_failed)=$FAILED check_failures=$CHK dropped=$(jq '.metrics.dropped_iterations.count // 0' out/k6-summary.json)"
jq -c '{avg_ms:.metrics.http_req_duration.avg, p95_ms:.metrics.http_req_duration["p(95)"], max_ms:.metrics.http_req_duration.max}' out/k6-summary.json
check "zero failed requests during roll-forward, undo and re-apply" test "$FAILED" = 0
echo "-- pod churn during the run (kubectl get pods -w, last 40 lines)"; tail -40 out/backend-pods-watch.txt
run k get pods -l app=backend -o wide

say "summary"; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" = 0 ]
