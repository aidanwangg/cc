from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _normalize(url: str) -> str:
    """Use the psycopg (v3) driver for Postgres URLs.

    Managed hosts (Render, Heroku, ...) hand out `postgres://` or
    `postgresql://` URLs; SQLAlchemy needs the explicit `+psycopg` driver
    suffix to use psycopg 3, which is what we install.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


database_url = _normalize(settings.database_url)
connect_args = (
    {"check_same_thread": False} if database_url.startswith("sqlite") else {}
)
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
