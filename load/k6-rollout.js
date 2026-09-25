// Steady, light load while the backend is rolled out and rolled back. Counts failures; does not stress the HPA.
// Run: DURATION=300s RPS=25 k6 run load/k6-rollout.js
import http from "k6/http";
import { check } from "k6";

export const options = {
  hosts: { "civicpulse.localtest.me": "127.0.0.1" },
  scenarios: {
    steady: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RPS || 25),
      timeUnit: "1s",
      duration: __ENV.DURATION || "300s",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
};

export default function () {
  const r = http.get("http://civicpulse.localtest.me/api/complaints?page=1&page_size=20", { timeout: "5s" });
  check(r, { "status 200": (x) => x.status === 200 });
}
