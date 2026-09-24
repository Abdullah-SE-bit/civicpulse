from sqlalchemy import create_engine

from alembic import context
from app.config import Settings

config = context.config


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or Settings.from_env().database_url


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    context.configure(url=_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
