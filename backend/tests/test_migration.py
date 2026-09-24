import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from tests.conftest import migrated_engine


def _insert(conn, **over):
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "text": "a valid complaint text",
        "location": "Street 1",
        "category": "water",
        "priority": "high",
        "triaged_by": "rules",
    }
    row.update(over)
    cols = ", ".join(row)
    vals = ", ".join(f":{k}" for k in row)
    conn.execute(text(f"INSERT INTO complaints ({cols}) VALUES ({vals})"), row)


def test_migration_creates_table_and_both_indexes(engine):
    insp = inspect(engine)
    assert "complaints" in insp.get_table_names()
    idx = {i["name"]: i["column_names"] for i in insp.get_indexes("complaints")}
    assert idx["ix_complaints_status_priority"] == ["status", "priority"]
    assert idx["ix_complaints_created_at"] == ["created_at"]


def test_status_defaults_to_open_and_timestamps_are_set(engine):
    with engine.begin() as conn:
        _insert(conn)
        row = conn.execute(text("SELECT status, created_at, updated_at FROM complaints")).one()
    assert row.status == "open" and row.created_at and row.updated_at


@pytest.mark.parametrize(
    "over",
    [
        {"text": "short"},
        {"text": "x" * 2001},
        {"location": "ab"},
        {"category": "potholes"},
        {"priority": "urgent"},
        {"status": "done"},
        {"triaged_by": "gpt"},
        {"ai_summary": "x" * 141},
    ],
)
def test_database_enforces_constraints_not_just_the_app(engine, over):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, **over)


def test_downgrade_removes_the_table(tmp_path):
    eng, cfg = migrated_engine(tmp_path)
    command.downgrade(cfg, "base")
    assert "complaints" not in inspect(eng).get_table_names()
