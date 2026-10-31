"""Multi-model sounding board: framework-based personas debate the idea, a Red Team attacks the
consensus, a chair synthesises. Pattern adapted from eduBITES soundingBoard's council engine."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .council_io import board_dossier, label, parse_vote, write_council
from .prompts import PROMPT_DIR, SCHEMA_DIR

__all__ = ["CouncilContext", "Persona", "Seat", "assemble_board", "board_dossier",
           "load_personas", "parse_vote", "run_council"]
PERSONAS_FILE = Path(__file__).parent / "personas.json"


@dataclass(frozen=True)
class Persona:
    role: str
    models: tuple
    system_prompt: str = ""
    frameworks: tuple = ()


@dataclass(frozen=True)
class Seat:
    persona: Persona
    alias: str


@dataclass
class CouncilContext:
    brief: object
    out_dir: Path
    chat: object
    structurer: object
    rounds: int = 1
    red_team: bool = True


def load_personas() -> tuple:
    raw = json.loads(PERSONAS_FILE.read_text())
    members = [Persona(p["role"], tuple(p["models"]), p["system_prompt"], tuple(p["frameworks"]))
               for p in raw["members"]]
    red = Persona(raw["red_team"]["role"], tuple(raw["red_team"]["models"]))
    chair = Persona(raw["synthesizer"]["role"], tuple(raw["synthesizer"]["models"]))
    return members, red, chair


def _candidates(persona: Persona, available: list) -> list:
    """Preferred models that are available, then every other available model."""
    preferred = [m for m in persona.models if m in available]
    return preferred + [m for m in available if m not in preferred]


def assemble_board(personas: list, available: list) -> list:
    """Seat each persona on its first available preferred model, else round-robin fallback."""
    if not available:
        return []
    seats = []
    for i, p in enumerate(personas):
        alias = next((m for m in p.models if m in available), available[i % len(available)])
        seats.append(Seat(p, alias))
    return seats


def _ask(ctx: CouncilContext, seat: Seat, prompts: tuple) -> dict:
    """One isolated model call; failures become an error entry instead of aborting the board."""
    base = {"role": seat.persona.role, "model": seat.alias}
    try:
        text = ctx.chat(seat.alias, prompts[0], prompts[1])
    except Exception as exc:  # provider down, bad key, timeout
        return {**base, "error": str(exc)[:300]}
    return {**base, "text": text, **parse_vote(text)}


def _ask_fallback(ctx: CouncilContext, seats: list, prompts: tuple) -> dict:
    """Try each candidate seat in order until one answers; return the last error otherwise."""
    out = {"error": "no candidate models"}
    for seat in seats:
        out = _ask(ctx, seat, prompts)
        if not out.get("error"):
            return out
    return out


def _opening(ctx: CouncilContext, board: list, dossier: str) -> list:
    skill = (PROMPT_DIR / "council_member.md").read_text()
    jobs = [(seat, (f"{seat.persona.system_prompt}\n\nFrameworks you own: "
                    f"{'; '.join(seat.persona.frameworks)}\n\n{skill}", dossier)) for seat in board]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(lambda j: _ask(ctx, j[0], j[1]), jobs))


def _debate_round(ctx: CouncilContext, board: list, latest: dict) -> list:
    """Turn-based: each member sees the freshest statement of everyone who already spoke."""
    template = (PROMPT_DIR / "council_debate.md").read_text()
    entries = []
    for seat in board:
        role = seat.persona.role
        if role not in latest:
            continue
        peers = "\n\n".join(f"### {r} said:\n{t}" for r, t in latest.items() if r != role)
        user = f"Your opening statement:\n{latest[role]}\n\nOther members (latest):\n\n{peers}"
        out = _ask(ctx, seat, (template.replace("{{role}}", role), user))
        if not out.get("error"):
            latest[role] = out["text"]
            entries.append(out)
    return entries


def _red_team(ctx: CouncilContext, seats: list, latest: dict) -> dict:
    digest = "\n\n".join(f"## {r}\n{t}" for r, t in latest.items())
    prompts = ((PROMPT_DIR / "council_redteam.md").read_text(),
               f"The board's positions:\n\n{digest}\n\nBuild the strongest case against them.")
    out = _ask_fallback(ctx, seats, prompts)
    return {**out, "position": label(out.get("text", ""), "Red Team")}


def _synthesize(ctx: CouncilContext, seats: list, transcript: str) -> dict:
    out = _ask_fallback(ctx, seats, ((PROMPT_DIR / "council_synthesis.md").read_text(), transcript))
    if out.get("error"):
        return {"chair_model": out.get("model", ""), "synthesis_markdown": "", "synthesis": {},
                "synthesis_error": out["error"]}
    schema = json.loads((SCHEMA_DIR / "council.json").read_text())
    return {"chair_model": out["model"], "synthesis_markdown": out["text"],
            "synthesis": ctx.structurer(out["text"], schema), "synthesis_error": ""}


def run_council(ctx: CouncilContext) -> dict:
    members, red, chair = load_personas()
    available = list(ctx.chat.available())
    board = assemble_board(members, available)
    if not board:
        raise RuntimeError("no council models available: add provider keys (see .env.example)")
    dossier = board_dossier(ctx.brief, ctx.out_dir)
    opening = _opening(ctx, board, dossier)
    latest = {m["role"]: m["text"] for m in opening if not m.get("error")}
    debate = [e for _ in range(max(0, ctx.rounds)) for e in _debate_round(ctx, board, latest)]
    seats = lambda p: [Seat(p, a) for a in _candidates(p, available)]  # noqa: E731
    rt = _red_team(ctx, seats(red), latest) if ctx.red_team and latest else None
    transcript = (f"{dossier}\n\n# Board transcript\n\n" + "\n\n".join(f"## {r}\n{t}" for r, t in latest.items())
                  + (f"\n\n# Red Team\n{rt.get('text', '')}" if rt else ""))
    data = {"idea": ctx.brief.slug, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "models": sorted({s.alias for s in board}), "rounds": ctx.rounds, "members": opening,
            "debate": debate, "red_team": rt, **_synthesize(ctx, seats(chair), transcript)}
    data["summary"] = data["synthesis"].get("summary", "")
    write_council(ctx.out_dir, data)
    return data
