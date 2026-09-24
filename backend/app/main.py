import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import Engine

from app import metrics
from app.config import Settings
from app.container import build_container
from app.db import make_engine, make_session_factory
from app.domain import InvalidTransitionError
from app.logging_setup import request_id_var, setup_logging
from app.providers.cache import make_redis
from app.providers.triage.base import TriageProvider
from app.providers.triage.factory import build_provider
from app.routes import complaints, ops
from app.services.complaints import ComplaintNotFoundError

log = logging.getLogger("civicpulse.http")


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    redis: Redis | None = None,
    provider: TriageProvider | None = None,
) -> FastAPI:
    setup_logging()
    settings = settings or Settings.from_env()
    engine = engine or make_engine(settings.database_url)
    redis = redis or make_redis(settings.redis_url)
    container = build_container(
        settings, engine, make_session_factory(engine), redis, provider or build_provider()
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        # uvicorn stops accepting and drains in-flight requests on SIGTERM before this runs.
        engine.dispose()
        redis.close()

    app = FastAPI(title="CivicPulse", lifespan=lifespan)
    app.state.container = container
    app.include_router(complaints.router)
    app.include_router(ops.router)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            elapsed = time.perf_counter() - start
            route = getattr(request.scope.get("route"), "path", "unmatched")
            metrics.HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            metrics.HTTP_LATENCY.labels(request.method, route).observe(elapsed)
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": round(elapsed * 1000, 1),
                },
            )
            request_id_var.reset(token)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        if any(e["loc"][0] == "path" for e in errors):
            return JSONResponse({"detail": "Complaint not found"}, status_code=404)
        return JSONResponse({"detail": errors}, status_code=400)

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition(request: Request, exc: InvalidTransitionError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ComplaintNotFoundError)
    async def not_found(request: Request, exc: ComplaintNotFoundError) -> JSONResponse:
        return JSONResponse({"detail": "Complaint not found"}, status_code=404)

    return app


app = create_app()
