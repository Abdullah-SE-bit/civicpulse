import uuid

import pytest

from app.domain import InvalidTransitionError, Status
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage
from app.repositories.complaints import ComplaintFilter, ComplaintRepository
from app.seed import seed
from app.services.complaints import ComplaintNotFoundError, ComplaintService
from app.services.triage_service import TriageService

TEXT = "Burst water main flooding Street 12, water entering ground floors"


def make(session, provider=None):
    triage = TriageService(provider or SimulatedTriage(), RuleBasedTriage(), sleep=lambda _: None)
    writes: list[int] = []
    svc = ComplaintService(ComplaintRepository(session), triage, lambda: writes.append(1))
    return svc, writes


def test_create_persists_triage_result_and_notifies(session):
    svc, writes = make(session)
    c = svc.create(TEXT, "Street 12", "0300-0000000")
    assert c.status == "open" and c.triaged_by == "simulated" and c.ai_summary
    assert c.triage_latency_ms is not None and writes == [1]
    assert svc.get(c.id).id == c.id


def test_failing_provider_still_creates_with_rules_fallback(session):
    svc, _ = make(session, SimulatedTriage("raise"))
    c = svc.create(TEXT, "Street 12", None)
    assert c.triaged_by == "rules:fallback"
    assert (c.category, c.priority) == ("water", "high")


def test_status_flow_and_terminal_state(session):
    svc, writes = make(session)
    c = svc.create(TEXT, "Street 12", None)
    assert svc.change_status(c.id, Status.in_progress).status == "in_progress"
    assert svc.change_status(c.id, Status.resolved).status == "resolved"
    with pytest.raises(InvalidTransitionError, match="resolved -> open"):
        svc.change_status(c.id, Status.open)
    assert len(writes) == 3  # create + two valid transitions; the rejected one is not a write


def test_unknown_id_is_not_found(session):
    svc, _ = make(session)
    with pytest.raises(ComplaintNotFoundError):
        svc.get(uuid.uuid4())


def test_list_filters_paginates_and_totals(session):
    seed(session)
    svc, _ = make(session)
    items, total = svc.search(ComplaintFilter(category="water"), page=1, page_size=4)
    assert total == 6 and len(items) == 4 and all(i.category == "water" for i in items)
    page2, _ = svc.search(ComplaintFilter(category="water"), page=2, page_size=4)
    assert len(page2) == 2
    high_open, n = svc.search(ComplaintFilter(status="open", priority="high"), 1, 100)
    assert n == len(high_open) > 0
    assert svc.search(ComplaintFilter(status="resolved"), 1, 10) == ([], 0)


def test_aggregates_and_recent_triage(session):
    seed(session)
    repo = ComplaintRepository(session)
    assert sum(repo.count_by("category").values()) == repo.total() == 32
    assert set(repo.count_by("priority")) == {"high", "normal", "low"}
    assert len(repo.recent_triage(20)) == 20
