"""The fixed stage backbone for a briefing session (server port of the front-end).

Five named stages; the agent may insert one adaptive follow-up within a stage. Kept
identical in spirit to ``apps/frontend/src/features/brief/stages.ts`` so the guided
experience matches whether driven by the SPA or an external client.
"""

from app.schemas.brief import BriefStep

BACKBONE_STEPS: list[BriefStep] = [
    BriefStep(
        id="work",
        stage="work",
        kind="text",
        prompt="What are you making a moodboard for?",
        helper="A project, a brand, a feeling — describe it in your own words.",
        forkable=True,
    ),
    BriefStep(
        id="feeling",
        stage="feeling",
        kind="chips",
        prompt="How should it feel?",
        helper="Pick the moods that fit, or add your own. A few is plenty.",
        seed_chips=[
            "Calm",
            "Energetic",
            "Premium",
            "Playful",
            "Editorial",
            "Minimal",
            "Bold",
            "Organic",
            "Technical",
            "Nostalgic",
        ],
        forkable=True,
    ),
    BriefStep(
        id="references",
        stage="references",
        kind="references",
        prompt="Bring in anything that inspires you.",
        helper="Add image URLs or notes. Optional.",
        forkable=False,
    ),
    BriefStep(
        id="palette",
        stage="palette",
        kind="palette",
        prompt="Where does the colour sit?",
        helper="Choose a few anchors, then dial the temperature and intensity.",
        forkable=True,
    ),
    BriefStep(
        id="audience",
        stage="audience",
        kind="text",
        prompt="Who's it for, and where will it live?",
        helper="Audience, context, medium — whatever matters most.",
        forkable=True,
    ),
]


def backbone_steps() -> list[BriefStep]:
    """Fresh copies of the backbone (so per-session mutation can't leak across sessions)."""
    return [step.model_copy(deep=True) for step in BACKBONE_STEPS]
