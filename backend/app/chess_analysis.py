"""PGN parsing and Stockfish evaluation.

This module produces the *structured grounding data* that gets fed to the
LLM: the move list, per-move engine evaluations, and a deterministically
detected turning point. The LLM never sees raw engine output — it sees a
compact, pre-digested summary built in coach.py.
"""

import io
from dataclasses import dataclass, field

import chess
import chess.engine
import chess.pgn

# Centipawn loss thresholds for the mover, matching common annotator conventions.
BLUNDER_CP = 200
MISTAKE_CP = 100
INACCURACY_CP = 50

# Mate scores are mapped onto the centipawn scale so swings stay comparable.
MATE_SCORE = 10_000


class PGNError(ValueError):
    """Raised when the submitted PGN can't be parsed into a playable game."""


@dataclass
class MoveRecord:
    ply: int
    move_number: int
    side: str  # "white" | "black"
    san: str
    uci: str


@dataclass
class MoveEval:
    ply: int
    move_number: int
    side: str
    san: str
    eval_cp: int  # evaluation after the move, centipawns from White's POV
    loss: int  # centipawns lost by the mover relative to the previous eval
    tag: str | None  # "blunder" | "mistake" | "inaccuracy" | None


@dataclass
class ParsedGame:
    white: str
    black: str
    result: str
    event: str | None
    date: str | None
    opening: str | None  # from PGN headers when present
    moves: list[MoveRecord] = field(default_factory=list)
    game: chess.pgn.Game | None = None


def parse_pgn(pgn_text: str) -> ParsedGame:
    pgn_text = pgn_text.strip()
    if not pgn_text:
        raise PGNError("Empty PGN.")

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise PGNError("Could not parse PGN.")
    if game.errors:
        raise PGNError(f"PGN contains errors: {game.errors[0]}")

    moves: list[MoveRecord] = []
    board = game.board()
    for ply, move in enumerate(game.mainline_moves(), start=1):
        moves.append(
            MoveRecord(
                ply=ply,
                move_number=(ply + 1) // 2,
                side="white" if board.turn == chess.WHITE else "black",
                san=board.san(move),
                uci=move.uci(),
            )
        )
        board.push(move)

    if not moves:
        raise PGNError("PGN contains no moves.")

    headers = game.headers
    return ParsedGame(
        white=headers.get("White", "White"),
        black=headers.get("Black", "Black"),
        result=headers.get("Result", "*"),
        event=headers.get("Event") or None,
        date=headers.get("Date") or None,
        opening=headers.get("Opening") or None,
        moves=moves,
        game=game,
    )


def _classify(loss: int) -> str | None:
    if loss >= BLUNDER_CP:
        return "blunder"
    if loss >= MISTAKE_CP:
        return "mistake"
    if loss >= INACCURACY_CP:
        return "inaccuracy"
    return None


def annotate_evals(moves: list[MoveRecord], evals_cp: list[int], start_cp: int = 0) -> list[MoveEval]:
    """Combine a move list with raw post-move evals into tagged MoveEvals.

    evals_cp[i] is the engine evaluation (White POV, centipawns) of the
    position after moves[i] was played. Separated from the engine call so the
    swing/turning-point logic is unit-testable without Stockfish.
    """
    annotated: list[MoveEval] = []
    prev = start_cp
    for record, cp in zip(moves, evals_cp):
        loss = (prev - cp) if record.side == "white" else (cp - prev)
        loss = max(loss, 0)
        annotated.append(
            MoveEval(
                ply=record.ply,
                move_number=record.move_number,
                side=record.side,
                san=record.san,
                eval_cp=cp,
                loss=loss,
                tag=_classify(loss),
            )
        )
        prev = cp
    return annotated


def evaluate_game(
    parsed: ParsedGame,
    stockfish_path: str,
    depth: int = 12,
    max_plies: int = 240,
) -> list[MoveEval]:
    """Run Stockfish over every position in the game and tag mistakes."""
    assert parsed.game is not None
    board = parsed.game.board()
    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
    try:
        limit = chess.engine.Limit(depth=depth)
        info = engine.analyse(board, limit)
        start_cp = info["score"].white().score(mate_score=MATE_SCORE)

        evals_cp: list[int] = []
        for record, move in zip(parsed.moves, parsed.game.mainline_moves()):
            if record.ply > max_plies:
                break
            board.push(move)
            info = engine.analyse(board, limit)
            evals_cp.append(info["score"].white().score(mate_score=MATE_SCORE))
    finally:
        engine.quit()

    return annotate_evals(parsed.moves[: len(evals_cp)], evals_cp, start_cp=start_cp)


def find_turning_point(evals: list[MoveEval]) -> MoveEval | None:
    """The single move with the largest centipawn loss for the mover."""
    flagged = [e for e in evals if e.loss > 0]
    if not flagged:
        return None
    return max(flagged, key=lambda e: e.loss)


def movetext(moves: list[MoveRecord]) -> str:
    """Render moves as standard numbered movetext: '1. e4 e5 2. Nf3 ...'."""
    parts: list[str] = []
    for m in moves:
        if m.side == "white":
            parts.append(f"{m.move_number}. {m.san}")
        else:
            parts.append(m.san)
    return " ".join(parts)


def format_cp(cp: int) -> str:
    if cp >= MATE_SCORE - 1000:
        return "winning (mate)"
    if cp <= -MATE_SCORE + 1000:
        return "losing (mate)"
    return f"{cp / 100:+.2f}"
