"""Deterministic direction curation and brief→text helpers.

The *structure* of divergent directions (which forks combine into which directions,
and the cap on how many) is deterministic — a port of the front-end's
``agent.composeDirections``. The LLM is reserved for the genuinely creative step
(authoring concepts + image prompts), not for this combinatorial bookkeeping.
"""

from app.ids import uid
from app.schemas.brief import (
    Answer,
    AnswerOption,
    BriefContent,
    BriefStep,
    Direction,
)

MAX_DIRECTIONS = 4

STAGE_TITLES = {
    "work": "The work",
    "feeling": "The feeling",
    "references": "References",
    "palette": "Palette",
    "audience": "Audience",
}


def summarize_option(option: AnswerOption) -> str:
    v = option.value
    if v.kind == "text":
        words = v.text.strip().split()
        if not words:
            return "—"
        return " ".join(words[:4]) + ("…" if len(words) > 4 else "")
    if v.kind == "chips":
        return ", ".join(v.chips[:3]) if v.chips else "—"
    if v.kind == "references":
        n = len(v.references)
        return f"{n} reference{'' if n == 1 else 's'}" if n else "—"
    # palette
    if not v.swatches and v.warmth == 0.5 and v.intensity == 0.5:
        return "—"
    temp = "warm" if v.warmth >= 0.6 else "cool" if v.warmth <= 0.4 else "balanced"
    energy = "vivid" if v.intensity >= 0.6 else "muted" if v.intensity <= 0.4 else "even"
    lead = (", ".join(v.swatches[:2]) + ", ") if v.swatches else ""
    return f"{lead}{temp} · {energy}"


def _branch_tag(option: AnswerOption) -> str:
    v = option.value
    if v.kind == "chips" and v.chips:
        return v.chips[0]
    if v.kind == "palette":
        if v.warmth >= 0.6:
            return "Warm"
        if v.warmth <= 0.4:
            return "Cool"
        return "Vivid" if v.intensity >= 0.6 else "Muted"
    if v.kind == "text" and v.text.strip():
        word = v.text.strip().split()[0]
        return word[:1].upper() + word[1:]
    return ""


def _step_by_id(content: BriefContent, step_id: str) -> BriefStep | None:
    return next((s for s in content.steps if s.id == step_id), None)


def _settled_highlights(content: BriefContent) -> list[str]:
    lines: list[str] = []
    for step in content.steps:
        answer = content.answers.get(step.id)
        if not answer or answer.skipped or not answer.options:
            continue
        summary = summarize_option(answer.options[0])
        if summary and summary != "—":
            lines.append(f"{STAGE_TITLES[step.stage]}: {summary}")
    return lines[:5]


def compose_directions(content: BriefContent) -> tuple[list[Direction], str | None]:
    """Curate a small, coherent set of directions from the forks. Never the naive
    cartesian product: capped at ``MAX_DIRECTIONS`` with the surplus summarised in a note."""
    forks: list[tuple[BriefStep, Answer]] = []
    for step in content.steps:
        answer = content.answers.get(step.id)
        if answer and not answer.skipped and len(answer.options) >= 2:
            forks.append((step, answer))

    if not forks:
        return [
            Direction(id=uid("dir"), name="Your brief", picks={}, highlights=_settled_highlights(content))
        ], None

    combos: list[dict[str, str]] = [{}]
    for step, answer in forks:
        nxt: list[dict[str, str]] = []
        for combo in combos:
            for option in answer.options:
                nxt.append({**combo, step.id: option.id})
        combos = nxt

    total = len(combos)
    note: str | None = None
    if total > MAX_DIRECTIONS:
        first = {s.id: a.options[0].id for s, a in forks}
        last = {s.id: a.options[-1].id for s, a in forks}
        mixed = {s.id: a.options[i % len(a.options)].id for i, (s, a) in enumerate(forks)}
        seen: set[str] = set()
        chosen: list[dict[str, str]] = []
        for combo in (first, mixed, last):
            key = repr(sorted(combo.items()))
            if key not in seen:
                seen.add(key)
                chosen.append(combo)
        combos = chosen
        note = f"{total} combinations were possible — focused into {len(combos)} distinct directions."

    directions: list[Direction] = []
    for i, picks in enumerate(combos):
        tags: list[str] = []
        highlights: list[str] = []
        for step, answer in forks:
            option = next((o for o in answer.options if o.id == picks.get(step.id)), None)
            if not option:
                continue
            tag = _branch_tag(option)
            if tag:
                tags.append(tag)
            highlights.append(f"{STAGE_TITLES[step.stage]}: {summarize_option(option)}")
        name = " · ".join(tags[:2]) or f"Direction {chr(65 + i)}"
        directions.append(Direction(id=uid("dir"), name=name, picks=picks, highlights=highlights))
    return directions, note


# ---- brief → text (context for the LLM author) ----


def _option_text(option: AnswerOption) -> str:
    v = option.value
    if v.kind == "text":
        return v.text.strip()
    if v.kind == "chips":
        return ", ".join(v.chips)
    if v.kind == "references":
        parts = [r.note or r.url or "" for r in v.references]
        return "; ".join(p for p in parts if p)
    temp = "warm" if v.warmth >= 0.6 else "cool" if v.warmth <= 0.4 else "balanced"
    energy = "vivid" if v.intensity >= 0.6 else "muted" if v.intensity <= 0.4 else "even"
    return f"{', '.join(v.swatches)} ({temp}, {energy})".strip()


def brief_to_text(content: BriefContent) -> str:
    """A readable summary of the whole brief, for the moodboard author prompt."""
    lines: list[str] = []
    for step in content.steps:
        answer = content.answers.get(step.id)
        if not answer or answer.skipped or not answer.options:
            continue
        title = STAGE_TITLES[step.stage]
        texts = [t for t in (_option_text(o) for o in answer.options) if t]
        if not texts:
            continue
        if len(texts) > 1:
            lines.append(f"{title}: {' OR '.join(texts)}")
        else:
            lines.append(f"{title}: {texts[0]}")
    return "\n".join(lines)


def direction_notes(content: BriefContent, direction: Direction) -> list[str]:
    """Highlights for a direction, falling back to the brief's settled highlights."""
    return direction.highlights or _settled_highlights(content)
