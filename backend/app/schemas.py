from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SkillLevel = Literal["beginner", "intermediate", "advanced"]


AnalysisTier = Literal["fast", "deep"]


class AnalyzeRequest(BaseModel):
    pgn: str
    skill_level: SkillLevel = "intermediate"
    coached_side: Literal["white", "black"] = "white"
    tier: AnalysisTier = "fast"


class TurningPoint(BaseModel):
    move_number: int = Field(description="Full-move number where the game turned")
    move: str = Field(description="The move in SAN, e.g. 'Nxe5'")
    player: Literal["white", "black"] = Field(description="Who played the move")
    explanation: str = Field(
        description="Why this move was the turning point: what it gave up or missed, "
        "and what should have been played instead, in plain language"
    )


class CoachReport(BaseModel):
    """Structured output schema for the Claude coaching response."""

    opening: str = Field(description="Name of the opening played, e.g. 'Italian Game'")
    headline: str = Field(description="One-sentence verdict on the game")
    turning_point: TurningPoint
    breakdown: str = Field(
        description="Conversational post-game breakdown, 2-4 short paragraphs separated "
        "by blank lines: how the game developed, what went wrong and why"
    )
    one_thing_to_work_on: str = Field(
        description="One concrete, practicable takeaway tailored to the player's level"
    )


class MoveEvalOut(BaseModel):
    ply: int
    move_number: int
    side: str
    san: str
    eval_cp: int
    loss: int
    tag: str | None


class AnalysisResponse(BaseModel):
    game_id: int
    white: str
    black: str
    result: str
    opening: str | None
    skill_level: SkillLevel
    engine_used: bool
    model: str
    evals: list[MoveEvalOut] | None
    report: CoachReport
    created_at: datetime


class GameSummary(BaseModel):
    id: int
    white: str
    black: str
    result: str
    opening: str | None
    skill_level: str
    headline: str | None
    created_at: datetime


class FeedbackRequest(BaseModel):
    rating: Literal["helpful", "not_helpful"]
    note: str | None = None


class ChesscomGame(BaseModel):
    white: str
    black: str
    white_rating: int | None
    black_rating: int | None
    result: str
    end_time: int | None  # unix timestamp
    time_class: str | None
    user_side: Literal["white", "black"] | None
    pgn: str
