from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    pgn: Mapped[str] = mapped_column(Text)
    white: Mapped[str] = mapped_column(String(120))
    black: Mapped[str] = mapped_column(String(120))
    result: Mapped[str] = mapped_column(String(16))
    opening: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skill_level: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="Analysis.id"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    model: Mapped[str] = mapped_column(String(60))
    engine_used: Mapped[bool] = mapped_column(default=False)
    engine_depth: Mapped[int | None] = mapped_column(nullable=True)
    evals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    report: Mapped[dict] = mapped_column(JSON)
    feedback_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    feedback_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    game: Mapped[Game] = relationship(back_populates="analyses")
