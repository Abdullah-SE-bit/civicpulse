from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.exceptions import RedisError

from app.container import Container
from app.deps import get_container, get_repo, get_stats_service
from app.repositories.complaints import ComplaintRepository, RepositoryUnavailableError
from app.schemas import StatsOut
from app.services.meta import provider_meta
from app.services.stats import StatsService

router = APIRouter()


@router.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness only. It must not touch Postgres or Redis: a failing probe restarts the pod."""
    return {"status": "ok"}


@router.get("/ready", tags=["ops"])
def ready(
    repo: ComplaintRepository = Depends(get_repo), c: Container = Depends(get_container)
) -> Response:
    """Readiness: a failing probe only removes the pod from the Service."""
    try:
        repo.ping()
    except RepositoryUnavailableError:
        return JSONResponse({"status": "unavailable", "failed": "postgres"}, status_code=503)
    try:
        c.limiter.ping()
    except RedisError:
        return JSONResponse({"status": "unavailable", "failed": "redis"}, status_code=503)
    return JSONResponse({"status": "ready"})


@router.get("/metrics", tags=["ops"])
def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/stats", response_model=StatsOut, tags=["stats"])
def stats(response: Response, svc: StatsService = Depends(get_stats_service)) -> dict[str, object]:
    data, cache_state = svc.get()
    response.headers["X-Cache"] = cache_state
    return data


@router.get("/api/meta/providers", tags=["meta"])
def providers(
    repo: ComplaintRepository = Depends(get_repo), c: Container = Depends(get_container)
) -> dict[str, object]:
    return provider_meta(repo, c.triage.provider_name)
