import { useEffect, useState } from "react";
import {
  analyzeGame,
  fetchChesscomGames,
  getGame,
  listGames,
  sendFeedback,
} from "./api.js";

const SKILL_LEVELS = ["beginner", "intermediate", "advanced"];

export default function App() {
  const [pgn, setPgn] = useState("");
  const [skillLevel, setSkillLevel] = useState("intermediate");
  const [coachedSide, setCoachedSide] = useState("white");
  const [tier, setTier] = useState("fast");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);

  const refreshHistory = () => listGames().then(setHistory).catch(() => {});

  useEffect(() => {
    refreshHistory();
  }, []);

  const onAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeGame(pgn, skillLevel, coachedSide, tier);
      setAnalysis(result);
      refreshHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const openGame = async (id) => {
    setError(null);
    try {
      setAnalysis(await getGame(id));
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <h2>Past games</h2>
        {history.length === 0 && <p className="muted">No games analyzed yet.</p>}
        <ul>
          {history.map((g) => (
            <li key={g.id}>
              <button className="history-item" onClick={() => openGame(g.id)}>
                <strong>
                  {g.white} vs {g.black}
                </strong>{" "}
                <span className="muted">{g.result}</span>
                {g.opening && <div className="muted small">{g.opening}</div>}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="main">
        <h1>♟ Chess Coach</h1>
        <p className="muted">
          Paste a PGN and get a post-game breakdown: what went wrong, why, and
          one thing to work on.
        </p>

        <ChesscomImport
          onPick={(game) => {
            setPgn(game.pgn);
            if (game.user_side) setCoachedSide(game.user_side);
          }}
        />

        <form onSubmit={onAnalyze}>
          <textarea
            value={pgn}
            onChange={(e) => setPgn(e.target.value)}
            placeholder={'[White "You"]\n[Black "Opponent"]\n\n1. e4 e5 2. Nf3 ...'}
            rows={8}
            required
          />
          <div className="controls">
            <label>
              I played{" "}
              <select
                value={coachedSide}
                onChange={(e) => setCoachedSide(e.target.value)}
              >
                <option value="white">white</option>
                <option value="black">black</option>
              </select>
            </label>
            <label>
              Explain it like I&apos;m…{" "}
              <select
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value)}
              >
                {SKILL_LEVELS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Coach{" "}
              <select value={tier} onChange={(e) => setTier(e.target.value)}>
                <option value="fast">fast (Haiku)</option>
                <option value="deep">deep (Opus)</option>
              </select>
            </label>
            <button type="submit" disabled={loading || !pgn.trim()}>
              {loading ? "Coach is reviewing…" : "Analyze game"}
            </button>
          </div>
        </form>

        {error && <div className="error">{error}</div>}
        {analysis && <Report analysis={analysis} />}
      </main>
    </div>
  );
}

function ChesscomImport({ onPick }) {
  const [username, setUsername] = useState("");
  const [games, setGames] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);

  const onFetch = async (e) => {
    e.preventDefault();
    setFetching(true);
    setError(null);
    try {
      setGames(await fetchChesscomGames(username.trim()));
    } catch (err) {
      setError(err.message);
      setGames(null);
    } finally {
      setFetching(false);
    }
  };

  return (
    <div className="card import">
      <form onSubmit={onFetch} className="import-form">
        <label htmlFor="chesscom-username">Import from Chess.com:</label>
        <input
          id="chesscom-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="your username"
        />
        <button type="submit" disabled={fetching || !username.trim()}>
          {fetching ? "Fetching…" : "Fetch recent games"}
        </button>
      </form>
      {error && <div className="error">{error}</div>}
      {games && games.length === 0 && (
        <p className="muted">No recent standard games found.</p>
      )}
      {games && games.length > 0 && (
        <ul className="import-list">
          {games.map((g, i) => (
            <li key={i}>
              <button type="button" className="history-item" onClick={() => onPick(g)}>
                <strong>
                  {g.white} vs {g.black}
                </strong>{" "}
                <span className="muted">
                  {g.result} · {g.time_class}
                  {g.end_time
                    ? ` · ${new Date(g.end_time * 1000).toLocaleDateString()}`
                    : ""}
                  {g.user_side ? ` · you were ${g.user_side}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Report({ analysis }) {
  const { report } = analysis;
  const [feedbackSent, setFeedbackSent] = useState(false);

  useEffect(() => setFeedbackSent(false), [analysis.game_id]);

  const rate = async (rating) => {
    try {
      await sendFeedback(analysis.game_id, rating);
      setFeedbackSent(true);
    } catch {
      // feedback is best-effort
    }
  };

  return (
    <section className="report">
      <header>
        <h2>{report.headline}</h2>
        <p className="muted">
          {analysis.white} vs {analysis.black} · {analysis.result} ·{" "}
          {report.opening}
          {analysis.engine_used ? " · engine-checked" : ""}
          {analysis.model ? ` · ${analysis.model}` : ""}
        </p>
      </header>

      <div className="card turning-point">
        <h3>
          Turning point: move {report.turning_point.move_number} (
          {report.turning_point.player}) — {report.turning_point.move}
        </h3>
        <p>{report.turning_point.explanation}</p>
      </div>

      <div className="breakdown">
        {report.breakdown.split(/\n\s*\n/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>

      <div className="card takeaway">
        <h3>One thing to work on</h3>
        <p>{report.one_thing_to_work_on}</p>
      </div>

      {analysis.evals && <EvalList evals={analysis.evals} />}

      <div className="feedback">
        {feedbackSent ? (
          <span className="muted">Thanks for the feedback!</span>
        ) : (
          <>
            <span className="muted">Was this helpful?</span>
            <button onClick={() => rate("helpful")}>👍</button>
            <button onClick={() => rate("not_helpful")}>👎</button>
          </>
        )}
      </div>
    </section>
  );
}

function EvalList({ evals }) {
  const flagged = evals.filter((e) => e.tag);
  if (flagged.length === 0) return null;
  return (
    <details className="card">
      <summary>Engine-flagged moves ({flagged.length})</summary>
      <ul>
        {flagged.map((e) => (
          <li key={e.ply}>
            <code>
              {e.move_number}
              {e.side === "white" ? ". " : "... "}
              {e.san}
            </code>{" "}
            — {e.tag} (cost {e.loss} cp)
          </li>
        ))}
      </ul>
    </details>
  );
}
