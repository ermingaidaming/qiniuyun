"""Database engine and async session factory."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_fks(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    """Enable SQLite foreign key enforcement on each connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session = async_sessionmaker(engine, expire_on_commit=False)


# Ensure tables exist at import time (idempotent). Tests use ASGITransport
# which doesn't trigger the lifespan. We use a sync engine because aiosqlite
# requires a running event loop for async operations.
from sqlalchemy import create_engine  # noqa: E402
from app.db.tables import Base  # noqa: E402

_sync_url = settings.database_url.replace("+aiosqlite", "")
_sync_engine = create_engine(_sync_url)


@event.listens_for(_sync_engine, "connect")
def _enable_sync_sqlite_fks(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


Base.metadata.create_all(_sync_engine)
_sync_engine.dispose()
