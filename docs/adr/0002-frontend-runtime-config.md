# ADR 0002: Frontend reaches the API through an nginx `/api` proxy

Status: accepted

## Context
Vite bakes `import.meta.env` values into the JavaScript bundle at build time. An absolute backend URL in the bundle would make the image environment-specific: a build for `localhost:8000` is wrong in Compose, and a build for the cluster is wrong on a laptop. That breaks build-once-deploy-many for the frontend.

## Decision
The frontend only ever calls same-origin `/api/...` (`frontend/src/api/client.ts`). In the image, nginx proxies `/api/` to `http://backend:8000` (`frontend/nginx.conf:7-8`). In `npm run dev`, the Vite dev server proxies `/api` (`frontend/vite.config.ts`, override with `VITE_DEV_BACKEND`). The same image runs unchanged in Compose and Kubernetes because both provide a name `backend` on port 8000. In Kubernetes the Ingress also routes `/api` straight to the backend Service (`k8s/base/ingress.yaml`); no rewrite is needed because the backend routes already start with `/api`.

nginx forwards `X-Forwarded-For` and `X-Request-ID`, which the backend reads for per-client rate limiting and log correlation.

## Alternatives
- `/config.js` generated at container start from environment variables: also valid and lets the browser call a different origin, but then the backend needs CORS and the entrypoint needs a templating step. Not needed while everything is behind one origin.
- `VITE_API_URL` at build time: rejected, see Context.

## Consequences
- No CORS configuration and no runtime templating step.
- The backend Service/host must be named `backend` on 8000, or the nginx upstream must change.
- Two components (nginx and Ingress) can route `/api`; the nginx route is what Compose uses, the Ingress route is what a browser uses in Kubernetes. Both are unrewritten. Not yet exercised on a real cluster.
- What would go wrong with a baked URL: rebuilding per environment means the tested artifact is not the deployed artifact.
