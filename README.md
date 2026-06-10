# ♟ Chess Coach

An AI-powered chess coaching platform that automatically syncs with a user's Chess.com account to provide highly contextual, conversational post-game reviews.

## Current Architecture

```
Chess.com API ──▶ FastAPI ──▶ python-chess (PGN parsing)
                    │
                    ├──▶ Stockfish (optional)   ← per-move evals, blunder detection
                    │         │
                    ├──▶ Claude (Haiku 4.5)      ← reasoning/explanation layer
                    │         structured grounding data in, typed CoachReport out
                    │
                    └──▶ SQLAlchemy ──▶ PostgreSQL (SQLite for local dev)
```

The key design idea: **the engine is the data source, the LLM is the
explanation layer.** When Stockfish is available, the backend evaluates every
position, computes per-move centipawn loss, tags inaccuracies / mistakes /
blunders, and deterministically identifies the turning point (largest swing).
That structured output is fed to Claude as grounding data — Claude's job is to
translate it into human coaching ("this left your queen stranded"), never to
quote centipawns. Without Stockfish, Claude identifies the turning point from
the move list itself.

### Prompt engineering notes

- **Frozen coaching persona** (`backend/app/coach.py`): the system prompt
  defines a consistent coach voice and is byte-identical across requests —
  all per-game data and parameters live in the user message (this is also
  what makes prompt caching possible as the prompt grows).
- **Skill-level parameterization**: `beginner` / `intermediate` / `advanced`
  maps to explicit guidance injected into the user message ("define 'fork'
  when you use it" vs. "concrete variations are welcome").
- **Structured outputs**: the response is constrained to a Pydantic schema
  (`CoachReport`: opening, headline, turning point, breakdown, one thing to
  work on) via the Messages API `output_format`, so the frontend renders
  typed fields instead of scraping prose.
- **Adaptive thinking** is enabled so the model reasons through the game
  before writing the report.

## Running it

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
# optional: engine grounding
export STOCKFISH_PATH=/usr/bin/stockfish      # auto-detected if on PATH
# optional: real database (defaults to local SQLite)
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/chess_coach

uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
```

### Tests

```bash
cd backend
python -m pytest
```

Tests cover PGN parsing, eval annotation / turning-point detection (with
synthetic evals, no Stockfish needed), and prompt construction.

## API

| Method | Path                       | Description                                  |
|--------|----------------------------|----------------------------------------------|
| POST   | `/api/games/analyze`       | `{pgn, skill_level}` → full coaching report  |
| GET    | `/api/games`               | Past games with headlines                    |
| GET    | `/api/games/{id}`          | A stored game's latest analysis              |
| POST   | `/api/games/{id}/feedback` | `{rating, note}` thumbs up/down on a report  |
| GET    | `/api/health`              | Reports model + whether Stockfish was found  |

## Status / roadmap

- [x] PGN parsing + validation
- [x] Stockfish integration (auto-detected; per-move evals → LLM grounding)
- [x] Turning point / biggest blunder detection
- [x] Skill-level-parameterized coaching prompt
- [x] Structured `CoachReport` output
- [x] Opening identification (PGN header, else Claude names it)
- [x] Game + feedback history (PostgreSQL-ready via SQLAlchemy)
- [ ] "Study plan" generator from your last 5 games
- [ ] Streaming the breakdown token-by-token to the UI (SSE)
- [ ] Alembic migrations (tables are auto-created for now)
