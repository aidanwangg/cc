// Chess.com import, done client-side (in the visitor's browser) rather than
// through our backend. Chess.com's Cloudflare blocks datacenter IPs (so a
// server-side fetch from Render fails), but each visitor's browser is on a
// residential connection that Chess.com allows, and the public API sends
// permissive CORS headers. The browser fetches the games, the user picks one,
// and only the chosen PGN is sent to our (gated) backend for analysis.
//
// This mirrors backend/app/chesscom.py so behavior matches local dev.

const DRAW_CODES = new Set([
  "agreed",
  "repetition",
  "stalemate",
  "insufficient",
  "50move",
  "timevsinsufficient",
]);

function resultString(white, black) {
  if (white.result === "win") return "1-0";
  if (black.result === "win") return "0-1";
  if (DRAW_CODES.has(white.result)) return "1/2-1/2";
  return "*";
}

function gamesFromArchive(archive, username) {
  const lower = username.toLowerCase();
  const games = [];
  for (const g of archive.games || []) {
    if (g.rules !== "chess" || !g.pgn) continue;
    const white = g.white || {};
    const black = g.black || {};
    let userSide = null;
    if ((white.username || "").toLowerCase() === lower) userSide = "white";
    else if ((black.username || "").toLowerCase() === lower) userSide = "black";
    games.push({
      white: white.username || "White",
      black: black.username || "Black",
      white_rating: white.rating ?? null,
      black_rating: black.rating ?? null,
      result: resultString(white, black),
      end_time: g.end_time ?? null,
      time_class: g.time_class ?? null,
      user_side: userSide,
      pgn: g.pgn,
    });
  }
  return games;
}

export async function fetchChesscomGamesClient(username, count = 10) {
  const u = username.trim();
  const archivesResp = await fetch(
    `https://api.chess.com/pub/player/${encodeURIComponent(u)}/games/archives`,
  );
  if (archivesResp.status === 404) {
    throw new Error(`Chess.com user '${u}' not found.`);
  }
  if (!archivesResp.ok) {
    throw new Error("Chess.com request failed. Try again in a moment.");
  }
  const { archives = [] } = await archivesResp.json();

  const collected = [];
  // Archives are oldest-first; walk newest-first until we have enough.
  for (const archiveUrl of [...archives].reverse()) {
    const monthResp = await fetch(archiveUrl);
    if (!monthResp.ok) continue;
    const monthGames = gamesFromArchive(await monthResp.json(), u);
    monthGames.sort((a, b) => (b.end_time || 0) - (a.end_time || 0));
    collected.push(...monthGames);
    if (collected.length >= count) break;
  }
  return collected.slice(0, count);
}
