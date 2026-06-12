"""Chess.com Published-Data API client.

Read-only and unauthenticated — no OAuth, no API key. Given a username, we
fetch the player's monthly game archives and pull recent games, each of which
already includes a PGN that drops straight into the analysis pipeline.

Chess.com throttles anonymous/parallel traffic, so requests are made serially
with an identifying User-Agent.
"""

import httpx

BASE_URL = "https://api.chess.com/pub"
USER_AGENT = "chess-coach-app (https://github.com/aidanwangg/cc)"

# Per-player result codes that count as a draw; everything else is a
# win for one side ("win") or a loss code (checkmated, resigned, timeout, ...).
_DRAW_CODES = {
    "agreed",
    "repetition",
    "stalemate",
    "insufficient",
    "50move",
    "timevsinsufficient",
}


class ChesscomError(RuntimeError):
    pass


class ChesscomUserNotFound(ChesscomError):
    pass


def _result_string(white: dict, black: dict) -> str:
    if white.get("result") == "win":
        return "1-0"
    if black.get("result") == "win":
        return "0-1"
    if white.get("result") in _DRAW_CODES:
        return "1/2-1/2"
    return "*"


def games_from_archive(archive_json: dict, username: str) -> list[dict]:
    """Extract standard-chess games from a monthly archive response.

    Pure function over the API payload so it's unit-testable without network.
    Variants (chess960, bughouse, ...) are skipped — their PGNs don't fit the
    standard analysis pipeline.
    """
    lower = username.lower()
    games: list[dict] = []
    for g in archive_json.get("games", []):
        if g.get("rules") != "chess" or not g.get("pgn"):
            continue
        white = g.get("white", {})
        black = g.get("black", {})
        if white.get("username", "").lower() == lower:
            user_side = "white"
        elif black.get("username", "").lower() == lower:
            user_side = "black"
        else:
            user_side = None
        games.append(
            {
                "white": white.get("username", "White"),
                "black": black.get("username", "Black"),
                "white_rating": white.get("rating"),
                "black_rating": black.get("rating"),
                "result": _result_string(white, black),
                "end_time": g.get("end_time"),
                "time_class": g.get("time_class"),
                "user_side": user_side,
                "pgn": g["pgn"],
            }
        )
    return games


def fetch_recent_games(username: str, count: int = 10) -> list[dict]:
    """Fetch the player's most recent standard games, newest first."""
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=15, follow_redirects=True
    ) as client:
        resp = client.get(f"{BASE_URL}/player/{username}/games/archives")
        if resp.status_code == 404:
            raise ChesscomUserNotFound(f"Chess.com user '{username}' not found.")
        resp.raise_for_status()
        archives: list[str] = resp.json().get("archives", [])

        collected: list[dict] = []
        # Archives are oldest-first; walk months newest-first until we have enough.
        for archive_url in reversed(archives):
            month_resp = client.get(archive_url)
            month_resp.raise_for_status()
            month_games = games_from_archive(month_resp.json(), username)
            month_games.sort(key=lambda g: g["end_time"] or 0, reverse=True)
            collected.extend(month_games)
            if len(collected) >= count:
                break

    return collected[:count]
