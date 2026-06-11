from app.chesscom import games_from_archive
from app.coach import model_for_tier, thinking_params
from app.config import settings

ARCHIVE = {
    "games": [
        {
            "rules": "chess",
            "time_class": "blitz",
            "end_time": 1700000300,
            "pgn": '[White "Aidan"]\n[Black "Rival"]\n\n1. e4 e5 1-0',
            "white": {"username": "Aidan", "rating": 1200, "result": "win"},
            "black": {"username": "Rival", "rating": 1180, "result": "checkmated"},
        },
        {
            # Variant games must be skipped.
            "rules": "chess960",
            "time_class": "blitz",
            "end_time": 1700000200,
            "pgn": "...",
            "white": {"username": "Aidan", "result": "win"},
            "black": {"username": "Other", "result": "resigned"},
        },
        {
            "rules": "chess",
            "time_class": "rapid",
            "end_time": 1700000100,
            "pgn": '[White "Rival"]\n[Black "AIDAN"]\n\n1. d4 d5 1/2-1/2',
            "white": {"username": "Rival", "rating": 1180, "result": "agreed"},
            "black": {"username": "AIDAN", "rating": 1200, "result": "agreed"},
        },
        {
            # Abandoned game with no PGN must be skipped.
            "rules": "chess",
            "white": {"username": "Aidan", "result": "win"},
            "black": {"username": "Other", "result": "abandoned"},
        },
    ]
}


def test_games_from_archive_filters_and_maps():
    games = games_from_archive(ARCHIVE, "aidan")
    assert len(games) == 2

    win = games[0]
    assert win["user_side"] == "white"
    assert win["result"] == "1-0"
    assert win["white_rating"] == 1200
    assert "1. e4 e5" in win["pgn"]

    # Username matching is case-insensitive, side detection follows the player.
    draw = games[1]
    assert draw["user_side"] == "black"
    assert draw["result"] == "1/2-1/2"
    assert draw["time_class"] == "rapid"


def test_games_from_archive_unrelated_user():
    games = games_from_archive(ARCHIVE, "somebody_else")
    assert all(g["user_side"] is None for g in games)


def test_model_for_tier():
    assert model_for_tier("fast") == settings.fast_model
    assert model_for_tier("deep") == settings.anthropic_model
    assert settings.fast_model.startswith("claude-haiku")
    assert settings.anthropic_model.startswith("claude-opus")


def test_thinking_params_gated_by_model():
    # Haiku 4.5 rejects adaptive thinking — the fast tier must not send it.
    assert thinking_params(settings.fast_model) == {}
    assert thinking_params(settings.anthropic_model) == {"thinking": {"type": "adaptive"}}
