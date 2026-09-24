from app.repositories.complaints import ComplaintRepository
from app.seed import seed
from app.seed_data import SEED_COMPLAINTS


def test_seed_has_at_least_30_and_covers_every_category():
    assert len(SEED_COMPLAINTS) >= 30
    assert {c for _, _, c, _ in SEED_COMPLAINTS} == {
        "water",
        "electricity",
        "sanitation",
        "roads",
        "streetlights",
        "other",
    }
    assert len({t for t, *_ in SEED_COMPLAINTS}) == len(SEED_COMPLAINTS)


def test_seed_is_idempotent(session):
    first = seed(session)
    total = ComplaintRepository(session).total()
    second = seed(session)
    assert first == len(SEED_COMPLAINTS) == total
    assert second == 0 and ComplaintRepository(session).total() == total
