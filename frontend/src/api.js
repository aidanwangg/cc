async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
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
