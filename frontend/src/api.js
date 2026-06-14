// In dev, leave VITE_API_BASE_URL unset so calls are relative and Vite's
// proxy forwards /api to the backend. In production, set it to the deployed
// backend URL (e.g. https://chess-coach-api.onrender.com).
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export const getPassword = () => localStorage.getItem("app_password") || "";
export const setPassword = (value) =>
  localStorage.setItem("app_password", value);

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-App-Password": getPassword(),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch {
      // non-JSON error body
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const analyzeGame = (pgn, skillLevel, coachedSide, tier) =>
  request("/api/games/analyze", {
    method: "POST",
    body: JSON.stringify({
      pgn,
      skill_level: skillLevel,
      coached_side: coachedSide,
      tier,
    }),
  });

export const fetchChesscomGames = (username, count = 10) =>
  request(
    `/api/chesscom/${encodeURIComponent(username)}/recent?count=${count}`,
  );

export const listGames = () => request("/api/games");

export const getGame = (id) => request(`/api/games/${id}`);

export const sendFeedback = (id, rating, note) =>
  request(`/api/games/${id}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, note }),
  });
