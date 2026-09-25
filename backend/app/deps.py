from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.container import Container
from app.repositories.complaints import ComplaintRepository
from app.services.complaints import ComplaintService
from app.services.stats import StatsService


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_session(c: Container = Depends(get_container)) -> Iterator[Session]:
    with c.session_factory() as session:
        yield session


def get_repo(session: Session = Depends(get_session)) -> ComplaintRepository:
    return ComplaintRepository(session)


def get_stats_service(
    repo: ComplaintRepository = Depends(get_repo), c: Container = Depends(get_container)
) -> StatsService:
    return StatsService(repo, c.stats_cache)


def get_complaint_service(
    repo: ComplaintRepository = Depends(get_repo),
    stats: StatsService = Depends(get_stats_service),
    c: Container = Depends(get_container),
) -> ComplaintService:
    return ComplaintService(repo, c.triage, on_write=stats.invalidate)


def client_id(request: Request) -> str:
    # Exactly one trusted proxy (nginx / ingress) sits in front and APPENDS the peer address it saw, so the LAST hop
    # is the only one a client cannot choose; earlier hops are whatever the client sent. ponytail: if the backend
    # is reachable directly (dev port 8000) the header is fully client-controlled; use a trusted-proxy list then.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, c: Container = Depends(get_container)) -> None:
    allowed, retry_after = c.limiter.hit(client_id(request))
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
