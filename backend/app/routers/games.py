import dataclasses
import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..chess_analysis import PGNError, evaluate_game, parse_pgn
from ..coach import CoachError, get_coaching_report, model_for_tier
from ..config import settings
from ..db import get_db
from ..schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    CoachReport,
    FeedbackRequest,
    GameSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games", tags=["games"])


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_game(req: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        parsed = parse_pgn(req.pgn)
    except PGNError as e:
        raise HTTPException(status_code=400, detail=str(e))

    evals = None
    stockfish = settings.resolve_stockfish()
    if stockfish:
        try:
            evals = evaluate_game(
                parsed,
                stockfish,
                depth=settings.stockfish_depth,
                max_plies=settings.stockfish_max_plies,
            )
        except Exception:
            logger.exception("Stockfish analysis failed; continuing without evals")

    coached_name = parsed.white if req.coached_side == "white" else parsed.black
    coached_player = f"{coached_name}, playing {req.coached_side.capitalize()}"
    model = model_for_tier(req.tier)

    try:
        report = get_coaching_report(parsed, evals, req.skill_level, coached_player, model)
    except CoachError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=502, detail="Anthropic API key is missing or invalid.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e.message}")

    game = models.Game(
        pgn=req.pgn.strip(),
        white=parsed.white,
        black=parsed.black,
        result=parsed.result,
        opening=parsed.opening or report.opening,
        skill_level=req.skill_level,
    )
    analysis = models.Analysis(
        model=model,
        engine_used=evals is not None,
        engine_depth=settings.stockfish_depth if evals is not None else None,
        evals=[dataclasses.asdict(e) for e in evals] if evals is not None else None,
        report=report.model_dump(),
    )
    game.analyses.append(analysis)
    db.add(game)
    db.commit()

    return _to_response(game, analysis)


@router.get("", response_model=list[GameSummary])
def list_games(db: Session = Depends(get_db)):
    games = db.scalars(select(models.Game).order_by(models.Game.id.desc())).all()
    return [
        GameSummary(
            id=g.id,
            white=g.white,
            black=g.black,
            result=g.result,
            opening=g.opening,
            skill_level=g.skill_level,
            headline=g.analyses[-1].report.get("headline") if g.analyses else None,
            created_at=g.created_at,
        )
        for g in games
    ]


@router.get("/{game_id}", response_model=AnalysisResponse)
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = db.get(models.Game, game_id)
    if game is None or not game.analyses:
        raise HTTPException(status_code=404, detail="Game not found")
    return _to_response(game, game.analyses[-1])


@router.post("/{game_id}/feedback", status_code=204)
def submit_feedback(game_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    game = db.get(models.Game, game_id)
    if game is None or not game.analyses:
        raise HTTPException(status_code=404, detail="Game not found")
    analysis = game.analyses[-1]
    analysis.feedback_rating = req.rating
    analysis.feedback_note = req.note
    db.commit()


def _to_response(game: models.Game, analysis: models.Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        game_id=game.id,
        white=game.white,
        black=game.black,
        result=game.result,
        opening=game.opening,
        skill_level=game.skill_level,
        engine_used=analysis.engine_used,
        model=analysis.model,
        evals=analysis.evals,
        report=CoachReport.model_validate(analysis.report),
        created_at=game.created_at,
    )
