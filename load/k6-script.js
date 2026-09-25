// Controlled load for observing the backend HPA. Run: k6 run load/k6-script.js
// Offered load is an open model (constant arrival rate), so it does not fall when the backend slows down.
// Env: BASE_URL (default via Ingress), HIGH_RPS, HOLD (default 240s).
import http from "k6/http";
import { check } from "k6";

const HIGH = Number(__ENV.HIGH_RPS || 120);
const HOLD = __ENV.HOLD || "240s";

export const options = {
  // The Ingress host resolves to 127.0.0.1 (kind maps host port 80 to the ingress controller).
  hosts: { "civicpulse.localtest.me": "127.0.0.1" },
  scenarios: {
    hpa_probe: {
      executor: "ramping-arrival-rate",
      startRate: 5,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { target: 5, duration: "30s" }, // baseline
        { target: HIGH, duration: "10s" }, // rise
        { target: HIGH, duration: HOLD }, // hold: this is where replicas should rise
        { target: 5, duration: "10s" }, // drop
        { target: 5, duration: "60s" }, // tail (scale-down is deliberately slow: stabilization 300 s)
      ],
    },
  },
};

const BASE = __ENV.BASE_URL || "http://civicpulse.localtest.me";

export default function () {
  // Heaviest read endpoint: 100-row page, serialisation + one query. Reads are not rate limited.
  const res = http.get(`${BASE}/api/complaints?page=1&page_size=100`);
  check(res, { "status 200": (r) => r.status === 200 });
}
