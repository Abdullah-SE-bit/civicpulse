import uuid
from collections.abc import Callable

from app.domain import Status, check_transition
from app.models import Complaint
from app.repositories.complaints import ComplaintFilter, ComplaintRepository
from app.services.triage_service import TriageService


class ComplaintNotFoundError(Exception):
    pass


class ComplaintService:
    """Business rules: triage orchestration on create, and the status state machine."""

    def __init__(
        self,
        repo: ComplaintRepository,
        triage: TriageService,
        on_write: Callable[[], None] = lambda: None,
    ) -> None:
        self._repo = repo
        self._triage = triage
        self._on_write = on_write

    def create(self, text: str, location: str, reporter_contact: str | None) -> Complaint:
        complaint_id = uuid.uuid4()
        outcome = self._triage.triage(text, location, complaint_id=str(complaint_id))
        complaint = Complaint(
            id=complaint_id,
            text=text,
            location=location,
            reporter_contact=reporter_contact,
            category=outcome.result.category.value,
            priority=outcome.result.priority.value,
            ai_summary=outcome.result.summary,
            triaged_by=outcome.triaged_by,
            triage_latency_ms=outcome.latency_ms,
        )
        self._repo.add(complaint)
        self._on_write()
        return complaint

    def get(self, complaint_id: uuid.UUID) -> Complaint:
        complaint = self._repo.get(complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(str(complaint_id))
        return complaint

    def search(
        self, flt: ComplaintFilter, page: int, page_size: int
    ) -> tuple[list[Complaint], int]:
        return self._repo.search(flt, page, page_size)

    def change_status(self, complaint_id: uuid.UUID, target: Status) -> Complaint:
        complaint = self.get(complaint_id)
        check_transition(Status(complaint.status), target)
        updated = self._repo.set_status(complaint, target.value)
        self._on_write()
        return updated
