import pytest
from alembic.config import Config

from alembic import command
from app.db import make_engine, make_session_factory


def migrated_engine(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return make_engine(url), cfg


@pytest.fixture
def engine(tmp_path):
    eng, _ = migrated_engine(tmp_path)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with make_session_factory(engine)() as s:
        yield s
