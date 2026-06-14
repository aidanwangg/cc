import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from ..chesscom import ChesscomUserNotFound, fetch_recent_games
from ..schemas import ChesscomGame
from ..security import require_password

router = APIRouter(
    prefix="/api/chesscom", tags=["chesscom"], dependencies=[Depends(require_password)]
)


@router.get("/{username}/recent", response_model=list[ChesscomGame])
def recent_games(username: str, count: int = Query(default=10, ge=1, le=25)):
    try:
        return fetch_recent_games(username, count)
    except ChesscomUserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Chess.com API request failed.")
