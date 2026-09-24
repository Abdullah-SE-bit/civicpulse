#!/bin/sh
# Runs versioned migrations (never app-startup DDL), optionally seeds, then hands over to the real command.
# Kubernetes: run migrations from one Job/initContainer and set RUN_MIGRATIONS=false on the replicas.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then alembic upgrade head; fi
if [ "${SEED_ON_START:-true}" = "true" ]; then python -m app.seed; fi
exec "$@"
