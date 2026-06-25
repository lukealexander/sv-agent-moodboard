"""LLM backends for the moodboard agent.

Two roles:
  * ``propose_followup`` — the adaptive in-stage refinement during briefing.
  * ``author_moodboard`` — compose a moodboard concept + palette + image prompts
    for one direction (the creative step before rendering).

``AnthropicLLM`` calls Claude (``claude-opus-4-8``, adaptive thinking, structured
outputs); ``StubLLM`` is deterministic so the service runs with no key and tests are
stable. The agent serves the *user's* brief — it never imposes a house style.
"""

import abc
import hashlib
import json

from pydantic import BaseModel


class FollowUp(BaseModel):
    prompt: str
    chips: list[str]


class PaletteSwatch(BaseModel):
    hex: str
    name: str


class ImageSpec(BaseModel):
    prompt: str
    alt: str


class MoodboardComposition(BaseModel):
    title: str
    summary: str
    notes: list[str]
    palette: list[PaletteSwatch]
    images: list[ImageSpec]


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    async def propose_followup(self, stage: str, chips: list[str]) -> FollowUp | None:
        """Optionally deepen a chips stage with one short refining question."""

    @abc.abstractmethod
    async def author_moodboard(
        self, brief_text: str, direction_name: str, direction_notes: list[str]
    ) -> MoodboardComposition:
        """Compose a moodboard concept, palette, and image prompts for one direction."""


# ---------------------------------------------------------------------------
# Stub
# ---------------------------------------------------------------------------

_FOLLOWUPS: dict[str, FollowUp] = {
    "Calm": FollowUp(
        prompt="What kind of calm?",
        chips=["Spa-calm", "Minimalist-calm", "Natural-calm", "Nocturnal-calm"],
    ),
    "Bold": FollowUp(
        prompt="Bold in which way?",
        chips=["Loud colour", "Oversized type", "High contrast", "Unexpected pairings"],
    ),
    "Editorial": FollowUp(
        prompt="What's the editorial reference?",
        chips=["Fashion glossy", "Independent zine", "Broadsheet", "Art-book"],
    ),
}

_SWATCHES: list[tuple[str, str]] = [
    ("Ink", "#1F2933"),
    ("Bone", "#EDE6D6"),
    ("Ember", "#C8643C"),
    ("Amber", "#E0A33D"),
    ("Clay", "#A8584A"),
    ("Rose", "#C9577B"),
    ("Plum", "#6B3FA0"),
    ("Indigo", "#3F4DA0"),
    ("Teal", "#2F9CB6"),
    ("Sage", "#6FA079"),
    ("Forest", "#2F6B4F"),
    ("Slate", "#566173"),
    ("Sand", "#D8C6A0"),
]

_TILE_ROLES = [
    "the overall mood",
    "colour and light",
    "texture and material",
    "a typographic detail",
    "composition and space",
]


class StubLLM(LLMProvider):
    async def propose_followup(self, stage: str, chips: list[str]) -> FollowUp | None:
        if stage != "feeling":
            return None
        for trigger, followup in _FOLLOWUPS.items():
            if trigger in chips:
                return followup
        return None

    async def author_moodboard(
        self, brief_text: str, direction_name: str, direction_notes: list[str]
    ) -> MoodboardComposition:
        seed = f"{brief_text}|{direction_name}|{'|'.join(direction_notes)}"
        digest = hashlib.sha256(seed.encode()).digest()
        start = digest[0] % len(_SWATCHES)
        step = (digest[1] % 4) + 1
        chosen: list[PaletteSwatch] = []
        seen: set[int] = set()
        i = start
        while len(chosen) < 5:
            if i % len(_SWATCHES) not in seen:
                seen.add(i % len(_SWATCHES))
                name, hexval = _SWATCHES[i % len(_SWATCHES)]
                chosen.append(PaletteSwatch(hex=hexval, name=name))
            i += step
        excerpt = brief_text.strip().split("\n")[0][:160] or "the brief"
        images = [
            ImageSpec(
                prompt=f"Moodboard tile exploring {role} for a {direction_name.lower()} direction — {excerpt}",
                alt=f"{role.capitalize()} — {direction_name}",
            )
            for role in _TILE_ROLES
        ]
        return MoodboardComposition(
            title=direction_name,
            summary=f"A {direction_name.lower()} direction for {excerpt}",
            notes=direction_notes or ["Composed from your brief."],
            palette=chosen,
            images=images,
        )


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

_FOLLOWUP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["followup"],
    "properties": {
        "followup": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["prompt", "chips"],
                    "properties": {
                        "prompt": {"type": "string"},
                        "chips": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ]
        }
    },
}

_COMPOSITION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "summary", "notes", "palette", "images"],
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
        "palette": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["hex", "name"],
                "properties": {"hex": {"type": "string"}, "name": {"type": "string"}},
            },
        },
        "images": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["prompt", "alt"],
                "properties": {"prompt": {"type": "string"}, "alt": {"type": "string"}},
            },
        },
    },
}


class AnthropicLLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _client(self):
        import anthropic  # lazy: only needed when a key is configured

        return anthropic.AsyncAnthropic(api_key=self.api_key)

    async def _structured(
        self, *, system: str, prompt: str, schema: dict, max_tokens: int
    ) -> dict:
        resp = await self._client().messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": schema}},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return json.loads(text)

    async def propose_followup(self, stage: str, chips: list[str]) -> FollowUp | None:
        if stage != "feeling" or not chips:
            return None
        data = await self._structured(
            system=(
                "You are a calm creative director helping shape a moodboard brief. "
                "Given the moods a designer chose, optionally propose ONE short refining "
                "follow-up question with 3-4 chip options. Only do so when it genuinely "
                "sharpens the direction; otherwise return null. Keep it warm and brief."
            ),
            prompt=f"Chosen moods: {', '.join(chips)}.",
            schema=_FOLLOWUP_SCHEMA,
            max_tokens=1024,
        )
        followup = data.get("followup")
        return FollowUp(**followup) if followup else None

    async def author_moodboard(
        self, brief_text: str, direction_name: str, direction_notes: list[str]
    ) -> MoodboardComposition:
        notes = "; ".join(direction_notes) if direction_notes else "(none specified)"
        data = await self._structured(
            system=(
                "You are an expert art director composing a moodboard. Serve the "
                "designer's brief and the chosen direction faithfully — do not impose a "
                "house style. Produce: a short title, a one-sentence summary, 2-4 concept "
                "notes, a palette of 5 swatches (hex + evocative name), and 5 image prompts "
                "(each a vivid, specific description suitable for an image generator) with "
                "concise alt text. The five images should cover different facets: overall "
                "mood, colour & light, texture & material, a typographic or detail study, "
                "and composition & space."
            ),
            prompt=(
                f"Brief:\n{brief_text}\n\nDirection: {direction_name}\nDirection notes: {notes}"
            ),
            schema=_COMPOSITION_SCHEMA,
            max_tokens=8000,
        )
        return MoodboardComposition(**data)
