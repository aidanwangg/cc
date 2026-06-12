import shutil

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App configuration, overridable via environment variables.

    DATABASE_URL defaults to a local SQLite file so the app runs with zero
    setup; point it at Postgres in real deployments, e.g.
    postgresql+psycopg://user:pass@localhost:5432/chess_coach
    """

    database_url: str = "sqlite:///./chess_coach.db"
    # "deep" tier: best quality, used when explicitly requested.
    anthropic_model: str = "claude-opus-4-8"
    # "fast" tier (default): ~5x cheaper; fine for engine-grounded explanation.
    fast_model: str = "claude-haiku-4-5"
    stockfish_path: str | None = None
    stockfish_depth: int = 12
    # Cap engine analysis so a 300-move PGN can't stall a request.
    stockfish_max_plies: int = 240
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    def resolve_stockfish(self) -> str | None:
        return self.stockfish_path or shutil.which("stockfish")


settings = Settings()
