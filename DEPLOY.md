# Deploying Chess Coach to Render

This deploys three things from one repo: the FastAPI backend (in Docker, so
Stockfish works), a managed Postgres database, and the React frontend as a
static site. Access is gated by a shared password you choose, and the paid
analyze endpoint is rate-limited per IP so a leaked password can't run up
your Claude bill.

## Prerequisites

- The repo pushed to GitHub (done).
- A [Render](https://render.com) account (free tier is fine).
- Your Anthropic API key with some credit.
- A password you'll hand out to the people you want to let in.

## Steps

### 1. Create the Blueprint

1. Render dashboard → **New** → **Blueprint**.
2. Connect this GitHub repo and pick the branch.
3. Render reads `render.yaml` and shows three resources: `chess-coach-db`,
   `chess-coach-api`, `chess-coach-web`. Click **Apply**.

### 2. Fill in the secrets

Render will prompt for the env vars marked `sync: false`:

| Service | Variable | Value |
|---|---|---|
| `chess-coach-api` | `ANTHROPIC_API_KEY` | your Claude key (`sk-ant-...`) |
| `chess-coach-api` | `APP_PASSWORD` | the password you'll share with users |
| `chess-coach-api` | `CORS_ORIGINS` | leave blank for now — set in step 4 |
| `chess-coach-web` | `VITE_API_BASE_URL` | leave blank for now — set in step 3 |

`DATABASE_URL` is wired automatically from the database.

### 3. Point the frontend at the backend

After the API service is live, copy its URL (e.g.
`https://chess-coach-api.onrender.com`). Set it as `VITE_API_BASE_URL` on
`chess-coach-web`, then trigger a redeploy of the web service (Vite bakes
env vars in at build time, so it must rebuild).

### 4. Let the frontend through CORS

Copy the web service's URL (e.g. `https://chess-coach-web.onrender.com`),
set it as `CORS_ORIGINS` on `chess-coach-api`, and let the API redeploy.

### 5. Use it

Open the web URL, type the access password in the top-right field, then
paste a PGN or import from Chess.com. Share the URL + password with whoever
you want to let in.

## Costs & limits to know

- **You pay for every analysis.** The password gate + the per-IP rate limit
  (`ANALYZE_RATE_LIMIT`, default `30/hour`) are your guardrails. Tighten the
  limit by setting that env var (e.g. `10/hour`).
- **Free tier sleeps.** Render's free web services spin down when idle; the
  first request after a nap takes ~30–60s to wake. Fine for a demo.
- **Free Postgres expires** ~90 days after creation — recreate it or upgrade
  before then if you want to keep history.
- **Rotate your key** if it's ever been pasted somewhere public.

## Local dev is unchanged

None of this affects local development. Locally, leave `APP_PASSWORD` unset
(the gate disables itself) and `VITE_API_BASE_URL` unset (Vite proxies to
`localhost:8000`).
