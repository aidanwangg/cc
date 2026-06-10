"""Claude coaching layer.

Architecture: Stockfish (when available) is the *data source* — it produces
per-move evaluations and a deterministic turning point. Claude is the
*reasoning and explanation layer* — it receives that structured grounding
data plus the move list and turns it into a conversational coaching
breakdown, calibrated to the player's skill level.

Prompt design notes:
- The system prompt (coaching persona) is frozen: per-game data and the
  skill-level parameter live in the user message, never in the system prompt.
- The response is constrained to the CoachReport schema via structured
  outputs, so the frontend renders typed fields instead of scraping prose.
"""

import anthropic

from .chess_analysis import MoveEval, ParsedGame, find_turning_point, format_cp, movetext
from .config import settings
from .schemas import CoachReport, SkillLevel

COACH_SYSTEM_PROMPT = """\
You are an experienced chess coach reviewing a student's game one-on-one.

Your coaching style:
- Warm and encouraging, but honest: name the mistakes plainly and explain them.
- You teach ideas, not engine lines. Talk about plans, piece activity, king
  safety, and pawn structure — not centipawns. Never mention "the engine",
  "evaluation", or numeric scores in your prose; translate them into chess
  meaning ("this loses a piece", "White's attack becomes unstoppable").
- Ground every claim in concrete moves from the game ("12...Qxb2 grabbed a
  pawn but left your queen stranded").
- When engine analysis is provided, treat it as ground truth for *what* the
  critical moments were; your job is to explain *why* in human terms.
- When no engine analysis is provided, identify the turning point yourself
  from the moves.
- Always speak directly to the player being coached ("you"), identified in
  each request.
- Pick exactly one turning point — the moment that most changed the game's
  outcome — even if there were several mistakes.
- The "one thing to work on" must be a specific, trainable habit or skill
  (e.g. "before every capture, check what recaptures and forks become
  possible"), not generic advice like "study tactics".
"""

# Skill level is a per-request parameter, injected into the user message so
# the system prompt stays byte-identical across requests.
SKILL_LEVEL_GUIDANCE: dict[str, str] = {
    "beginner": (
        "The player is a BEGINNER. Avoid jargon (no 'zwischenzug', 'prophylaxis'); "
        "if you use a term like 'fork' or 'pin', briefly say what it means. Focus on "
        "the most fundamental lesson in the game: piece safety, basic tactics, "
        "development, king safety. Keep variations to single moves."
    ),
    "intermediate": (
        "The player is INTERMEDIATE (club level). Standard chess terms are fine "
        "without definition. Discuss plans and typical structures, and you may give "
        "short concrete lines (2-3 moves) where they sharpen the point."
    ),
    "advanced": (
        "The player is ADVANCED (strong club / tournament player). Be precise and "
        "direct. Discuss subtleties: move-order nuances, long-term weaknesses, "
        "conversion technique. Concrete variations are welcome where they matter."
    ),
}


def build_game_summary(
    parsed: ParsedGame,
    evals: list[MoveEval] | None,
    coached_player: str,
    skill_level: SkillLevel,
) -> str:
    """Render the structured game data Claude reasons over."""
    lines = [
        f"White: {parsed.white}",
        f"Black: {parsed.black}",
        f"Result: {parsed.result}",
    ]
    if parsed.event:
        lines.append(f"Event: {parsed.event}")
    if parsed.opening:
        lines.append(f"Opening (from PGN header): {parsed.opening}")
    lines.append(f"\nYou are coaching: {coached_player}")
    lines.append(f"\n{SKILL_LEVEL_GUIDANCE[skill_level]}")

    lines.append("\nMoves:")
    lines.append(movetext(parsed.moves))

    if evals:
        flagged = [e for e in evals if e.tag]
        lines.append(
            "\nEngine analysis (Stockfish, centipawns from White's point of view). "
            "Use this as ground truth but never quote numbers in your answer:"
        )
        if flagged:
            lines.append("Flagged moves (eval is the position AFTER the move):")
            for e in flagged:
                dots = "." if e.side == "white" else "..."
                lines.append(
                    f"- {e.move_number}{dots}{e.san} ({e.side}): {e.tag.upper()}, "
                    f"eval {format_cp(e.eval_cp)}, cost the mover {e.loss} centipawns"
                )
        else:
            lines.append("No inaccuracies, mistakes, or blunders were flagged.")

        turning = find_turning_point(evals)
        if turning:
            dots = "." if turning.side == "white" else "..."
            lines.append(
                f"\nThe engine identifies the turning point as "
                f"{turning.move_number}{dots}{turning.san} by {turning.side} "
                f"(largest single swing of the game)."
            )
    else:
        lines.append(
            "\nNo engine analysis is available for this game. Identify the turning "
            "point yourself from the move list."
        )

    lines.append(
        "\nGive your post-game coaching breakdown now, following the report schema."
    )
    return "\n".join(lines)


class CoachError(RuntimeError):
    pass


def get_coaching_report(
    parsed: ParsedGame,
    evals: list[MoveEval] | None,
    skill_level: SkillLevel,
    coached_player: str = "the player with the White pieces",
) -> CoachReport:
    client = anthropic.Anthropic()
    prompt = build_game_summary(parsed, evals, coached_player, skill_level)

    response = client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=COACH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_format=CoachReport,
    )

    if response.stop_reason == "refusal":
        raise CoachError("The model declined to analyze this game.")
    if response.parsed_output is None:
        raise CoachError("The model did not return a valid coaching report.")
    return response.parsed_output
