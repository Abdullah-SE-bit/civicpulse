"""Runs against real PostgreSQL and Redis. Skipped unless LIVE_DATABASE_URL and LIVE_REDIS_URL are set
(the backend-live workflow sets them from service containers)."""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

import httpx
import pytest
import redis as redis_lib
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import DataError, IntegrityError

from alembic import command
from app.config import Settings
from app.db import make_engine, make_session_factory
from app.main import create_app
from app.providers.triage.simulated import SimulatedTriage
from app.repositories.complaints import ComplaintRepository
from app.seed import seed
from app.seed_data import SEED_COMPLAINTS

DB_URL = os.environ.get("LIVE_DATABASE_URL", "")
REDIS_URL = os.environ.get("LIVE_REDIS_URL", "")
pytestmark = pytest.mark.skipif(not (DB_URL and REDIS_URL), reason="live services not configured")

TEXT = "Burst water main flooding Street 12 since fajr, water entering ground floors"


def alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DB_URL)
    return cfg


@pytest.fixture
def pg():
    cfg = alembic_cfg()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = make_engine(DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def real_redis():
    r = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
    r.flushdb()
    yield r
    r.flushdb()
    r.close()


def test_migration_goes_up_down_and_up_again():
    cfg = alembic_cfg()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    assert "complaints" not in inspect(make_engine(DB_URL)).get_table_names()
    command.upgrade(cfg, "head")
    insp = inspect(make_engine(DB_URL))
    idx = {i["name"]: i["column_names"] for i in insp.get_indexes("complaints")}
    assert idx["ix_complaints_status_priority"] == ["status", "priority"]
    assert idx["ix_complaints_created_at"] == ["created_at"]


def test_timestamps_are_timestamptz_and_ids_are_uuid(pg):
    with pg.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'complaints' AND column_name IN ('created_at','updated_at','id')"
            )
        ).all()
    assert dict(rows) == {
        "created_at": "timestamp with time zone",
        "updated_at": "timestamp with time zone",
        "id": "uuid",
    }


@pytest.mark.parametrize(
    "over",
    [
        {"text": "short"},
        {"text": "x" * 2001},
        {"location": "ab"},
        {"category": "potholes"},
        {"priority": "urgent"},
        {"status": "done"},
        {"triaged_by": "llm:openrouter"},
        {"ai_summary": "x" * 141},
    ],
)
def test_postgres_enforces_the_constraints(pg, over):
    row = {
        "id": str(uuid.uuid4()),
        "text": "a valid complaint text",
        "location": "Street 1",
        "category": "water",
        "priority": "high",
        "triaged_by": "rules",
    }
    row.update(over)
    cols, vals = ", ".join(row), ", ".join(f":{k}" for k in row)
    # Postgres rejects an over-long varchar as DataError before any CHECK runs; everything else is an IntegrityError.
    with pytest.raises((IntegrityError, DataError)), pg.begin() as conn:
        conn.execute(text(f"INSERT INTO complaints ({cols}) VALUES ({vals})"), row)


def test_seed_is_idempotent_on_postgres(pg):
    with make_session_factory(pg)() as s:
        assert seed(s) == len(SEED_COMPLAINTS)
        assert seed(s) == 0
        assert ComplaintRepository(s).total() == len(SEED_COMPLAINTS)


def make_client(pg, real_redis, limit=1000, provider=None):
    settings = Settings(DB_URL, REDIS_URL, limit)
    return TestClient(create_app(settings, pg, real_redis, provider or SimulatedTriage()))


def test_stats_cache_and_invalidation_against_real_redis(pg, real_redis):
    with make_client(pg, real_redis) as c:
        assert c.get("/ready").status_code == 200
        assert c.get("/api/stats").headers["X-Cache"] == "MISS"
        assert c.get("/api/stats").headers["X-Cache"] == "HIT"
        assert 0 < real_redis.ttl("stats:v1") <= 30
        created = c.post("/api/complaints", json={"text": TEXT, "location": "Street 12"})
        assert created.status_code == 201
        after = c.get("/api/stats")
        assert after.headers["X-Cache"] == "MISS" and after.json()["total"] == 1
        fetched = c.get(f"/api/complaints/{created.json()['id']}").json()
        assert fetched["created_at"].endswith(("Z", "+00:00"))  # timezone-aware from Postgres


def test_triage_result_is_cached_in_real_redis_for_24h(pg, real_redis):
    provider = SimulatedTriage()
    with make_client(pg, real_redis, provider=provider) as c:
        for _ in range(3):
            assert c.post("/api/complaints", json={"text": TEXT, "location": "Street 12"}).status_code == 201
    assert provider.calls == 1
    keys = [k for k in real_redis.keys("triage:*")]
    assert len(keys) == 1 and 86000 < real_redis.ttl(keys[0]) <= 86400


def test_rate_limiter_uses_shared_redis_and_sets_retry_after(pg, real_redis):
    with make_client(pg, real_redis, limit=3) as a, make_client(pg, real_redis, limit=3) as b:
        body = {"text": TEXT, "location": "Street 12"}
        assert [a.post("/api/complaints", json=body).status_code for _ in range(2)] == [201, 201]
        assert b.post("/api/complaints", json=body).status_code == 201
        blocked = a.post("/api/complaints", json=body)
    assert blocked.status_code == 429 and 0 < int(blocked.headers["Retry-After"]) <= 60


def test_ready_reports_redis_down(pg):
    dead = redis_lib.Redis.from_url("redis://127.0.0.1:1/0", decode_responses=True, socket_connect_timeout=1)
    with make_client(pg, dead) as c:
        r = c.get("/ready")
    assert r.status_code == 503 and r.json()["failed"] == "redis"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX SIGTERM semantics")
def test_sigterm_lets_the_in_flight_request_finish_then_exits(pg, real_redis):
    port = free_port()
    env = {
        **os.environ,
        "DATABASE_URL": DB_URL,
        "REDIS_URL": REDIS_URL,
        "TRIAGE_PROVIDER": "simulated",
        "SIMULATED_LATENCY_MS": "3000",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        else:
            pytest.fail("server did not start")

        result: dict[str, httpx.Response] = {}

        def slow_post() -> None:
            result["r"] = httpx.post(
                f"{base}/api/complaints",
                json={"text": f"{TEXT} {uuid.uuid4()}", "location": "Street 12"},
                timeout=30,
            )

        t = threading.Thread(target=slow_post)
        t.start()
        time.sleep(1.0)  # the request is now inside the 3 s triage call
        started = time.monotonic()
        proc.send_signal(signal.SIGTERM)
        t.join(20)
        assert "r" in result and result["r"].status_code == 201, "in-flight request was dropped"
        assert time.monotonic() - started >= 1.0  # it finished after SIGTERM, not before
        code = proc.wait(timeout=20)
        # uvicorn re-raises the signal once it has drained, so a clean drain is 0 or -SIGTERM.
        assert code in (0, -signal.SIGTERM), f"unexpected exit code {code}"
        with make_session_factory(pg)() as s:
            assert ComplaintRepository(s).total() == 1  # the drained request was persisted
    finally:
        if proc.poll() is None:
            proc.kill()
        out = proc.stdout.read() if proc.stdout else ""
        print(out)
