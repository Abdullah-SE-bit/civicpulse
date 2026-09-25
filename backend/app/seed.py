"""Idempotent seed: `python -m app.seed`. Deterministic ids mean re-running inserts nothing."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.db import make_engine, make_session_factory
from app.models import Complaint
from app.repositories.complaints import ComplaintRepository
from app.seed_data import SEED_COMPLAINTS

_NAMESPACE = uuid.UUID("6f1d0c1e-5a52-4a55-9b1a-2f0c5b1c9a10")


def seed(session: Session) -> int:
    repo = ComplaintRepository(session)
    ids = {text: uuid.uuid5(_NAMESPACE, text) for text, *_ in SEED_COMPLAINTS}
    present = repo.existing_ids(list(ids.values()))
    now = datetime.now(UTC)
    new = [
        Complaint(
            id=ids[text],
            text=text,
            location=location,
            category=category,
            priority=priority,
            ai_summary=text[:140],
            triaged_by="rules",
            triage_latency_ms=0,
            created_at=now - timedelta(hours=i),
        )
        for i, (text, location, category, priority) in enumerate(SEED_COMPLAINTS)
        if ids[text] not in present
    ]
    repo.add_many(new)
    return len(new)


def main() -> None:
    engine = make_engine(Settings.from_env().database_url)
    with make_session_factory(engine)() as session:
        print(f"seeded {seed(session)} new complaints")


if __name__ == "__main__":
    main()
