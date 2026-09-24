import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Complaint


class RepositoryUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class ComplaintFilter:
    category: str | None = None
    priority: str | None = None
    status: str | None = None


class ComplaintRepository:
    """All SQL for complaints lives here and nowhere else."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def ping(self) -> None:
        try:
            self._s.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise RepositoryUnavailableError(str(exc)) from exc

    def add(self, complaint: Complaint) -> Complaint:
        self._s.add(complaint)
        self._s.commit()
        return complaint

    def get(self, complaint_id: uuid.UUID) -> Complaint | None:
        return self._s.get(Complaint, complaint_id)

    def search(self, flt: ComplaintFilter, page: int, page_size: int) -> tuple[list[Complaint], int]:
        conds = []
        if flt.category:
            conds.append(Complaint.category == flt.category)
        if flt.priority:
            conds.append(Complaint.priority == flt.priority)
        if flt.status:
            conds.append(Complaint.status == flt.status)
        total = self._s.scalar(select(func.count()).select_from(Complaint).where(*conds)) or 0
        rows = self._s.scalars(
            select(Complaint)
            .where(*conds)
            .order_by(Complaint.created_at.desc(), Complaint.id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        return list(rows), total

    def set_status(self, complaint: Complaint, status: str) -> Complaint:
        complaint.status = status
        self._s.commit()
        return complaint

    def count_by(self, column: str) -> dict[str, int]:
        col = {"category": Complaint.category, "priority": Complaint.priority}[column]
        rows = self._s.execute(select(col, func.count()).group_by(col)).all()
        return {k: n for k, n in rows}

    def total(self) -> int:
        return self._s.scalar(select(func.count()).select_from(Complaint)) or 0

    def recent_triage(self, limit: int = 20) -> list[tuple[str, int | None]]:
        rows = self._s.execute(
            select(Complaint.triaged_by, Complaint.triage_latency_ms)
            .order_by(Complaint.created_at.desc())
            .limit(limit)
        ).all()
        return [(by, ms) for by, ms in rows]

    def existing_ids(self, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return set(self._s.scalars(select(Complaint.id).where(Complaint.id.in_(ids))))

    def add_many(self, complaints: list[Complaint]) -> None:
        self._s.add_all(complaints)
        self._s.commit()
