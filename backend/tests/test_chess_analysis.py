import pytest

from app.chess_analysis import (
    PGNError,
    annotate_evals,
    find_turning_point,
    movetext,
    parse_pgn,
)
from app.coach import build_game_summary

SCHOLARS_MATE = """\
[Event "Casual Game"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


def test_parse_pgn_headers_and_moves():
    parsed = parse_pgn(SCHOLARS_MATE)
    assert parsed.white == "Alice"
    assert parsed.black == "Bob"
    assert parsed.result == "1-0"
    assert len(parsed.moves) == 7
    assert parsed.moves[0].san == "e4"
    assert parsed.moves[0].side == "white"
    assert parsed.moves[-1].san == "Qxf7#"
    assert parsed.moves[-1].move_number == 4


def test_parse_pgn_rejects_garbage():
    with pytest.raises(PGNError):
        parse_pgn("this is not a chess game")
    with pytest.raises(PGNError):
        parse_pgn("")


def test_movetext_round_trip():
    parsed = parse_pgn(SCHOLARS_MATE)
    assert movetext(parsed.moves) == "1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#"


def test_annotate_evals_flags_blunder_for_correct_side():
    parsed = parse_pgn(SCHOLARS_MATE)
    # Post-move evals (White POV): Bob's 3...Nf6 allows mate — a huge swing.
    evals_cp = [30, 25, 20, 15, 40, 350, 9990]
    annotated = annotate_evals(parsed.moves, evals_cp, start_cp=20)

    blunder = annotated[5]  # 3...Nf6
    assert blunder.san == "Nf6"
    assert blunder.side == "black"
    assert blunder.loss == 310
    assert blunder.tag == "blunder"

    # White's good moves must not be charged a loss for improving the eval.
    assert annotated[4].loss == 0  # 3. Bc4: 15 -> 40 helps White


def test_find_turning_point_picks_largest_swing():
    parsed = parse_pgn(SCHOLARS_MATE)
    evals_cp = [30, 25, 20, 15, 40, 350, 9990]
    annotated = annotate_evals(parsed.moves, evals_cp, start_cp=20)
    turning = find_turning_point(annotated)
    assert turning is not None
    # 4. Qxf7# swings 350 -> 9990 but that's a gain for the mover (white);
    # the largest *loss* is Black allowing it with 3...Nf6... except 9990-350
    # is charged to no one (white gained). Largest loss is 3...Nf6 (310).
    assert turning.san == "Nf6"


def test_game_summary_includes_engine_grounding():
    parsed = parse_pgn(SCHOLARS_MATE)
    evals_cp = [30, 25, 20, 15, 40, 350, 9990]
    annotated = annotate_evals(parsed.moves, evals_cp, start_cp=20)
    summary = build_game_summary(parsed, annotated, "Bob (Black)", "beginner")
    assert "1. e4 e5" in summary
    assert "BLUNDER" in summary
    assert "turning point" in summary
    assert "BEGINNER" in summary
    assert "coaching: Bob (Black)" in summary


def test_game_summary_without_engine():
    parsed = parse_pgn(SCHOLARS_MATE)
    summary = build_game_summary(parsed, None, "Bob (Black)", "advanced")
    assert "No engine analysis is available" in summary
    assert "ADVANCED" in summary
