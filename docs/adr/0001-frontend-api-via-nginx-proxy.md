# ADR 0001: Frontend reaches the API through an nginx `/api` proxy

Status: accepted

## Context
Vite bakes `import.meta.env` values into the JS bundle at build time. An absolute backend URL in the bundle would make the image environment-specific and break build-once-deploy-many (spec §2.1).

## Decision
The frontend only ever calls same-origin `/api/...`. In the image, nginx proxies `/api/` to `backend:8000`; in `npm run dev`, the Vite dev server proxies it (`VITE_DEV_BACKEND`, default `http://localhost:8000`). The same image runs unchanged in Compose and Kubernetes as long as a Service/host named `backend` exists.

## Consequences
- No CORS needed for the browser path, no `config.js` step at container start.
- The Kubernetes Service for the backend must be named `backend` (or the nginx upstream must be templated later).
- nginx must forward `X-Request-ID` (done) so logs correlate.
