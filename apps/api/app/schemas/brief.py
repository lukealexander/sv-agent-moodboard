"""Brief domain + API schemas.

The brief is a multi-step structure mirroring the front-end flow, kept
server-authoritative so any client (a product, another AI) gets the same guided
experience. The fixed backbone of stages is in ``app.services.stages``; this module
defines the values, answers, steps, and directions that flow over the wire and into
``BriefSession.state``.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

StageId = Literal["work", "feeling", "references", "palette", "audience"]
InputKind = Literal["text", "chips", "references", "palette"]


# ---- Answer values (discriminated by `kind`) ----


class TextValue(BaseModel):
    kind: Literal["text"] = "text"
    text: str = ""


class ChipsValue(BaseModel):
    kind: Literal["chips"] = "chips"
    chips: list[str] = Field(default_factory=list)


class ReferenceItem(BaseModel):
    url: str | None = None
    note: str | None = None


class ReferencesValue(BaseModel):
    kind: Literal["references"] = "references"
    references: list[ReferenceItem] = Field(default_factory=list)


class PaletteValue(BaseModel):
    kind: Literal["palette"] = "palette"
    swatches: list[str] = Field(default_factory=list)  # hex strings
    warmth: float = 0.5  # 0 cool .. 1 warm
    intensity: float = 0.5  # 0 muted .. 1 vivid


AnswerValue = Annotated[
    Union[TextValue, ChipsValue, ReferencesValue, PaletteValue],
    Field(discriminator="kind"),
]


class AnswerOption(BaseModel):
    id: str
    value: AnswerValue


class Answer(BaseModel):
    """The answer to one step. ``options`` length 1 is settled, >= 2 is a fork."""

    step_id: str
    options: list[AnswerOption] = Field(default_factory=list)
    skipped: bool = False


class BriefStep(BaseModel):
    """A question with an input. Backbone steps are fixed; ``adaptive`` ones are
    agent follow-ups inserted within a stage."""

    id: str
    stage: StageId
    kind: InputKind
    prompt: str
    helper: str | None = None
    seed_chips: list[str] | None = None
    forkable: bool = True
    adaptive: bool = False


class Direction(BaseModel):
    id: str
    name: str
    # forked step_id -> chosen option id
    picks: dict[str, str] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)


class BriefContent(BaseModel):
    """The full persisted state of a briefing session."""

    steps: list[BriefStep] = Field(default_factory=list)
    answers: dict[str, Answer] = Field(default_factory=dict)
    processed_stages: list[StageId] = Field(default_factory=list)
    directions: list[Direction] = Field(default_factory=list)
    note: str | None = None


# ---- API I/O ----


class AnswerRequest(BaseModel):
    """Answer the current step. Provide a single ``value`` (settled) or multiple
    ``options`` (a fork), or set ``skip`` to pass on the question."""

    value: AnswerValue | None = None
    options: list[AnswerValue] | None = None
    skip: bool = False


class BriefSessionResponse(BaseModel):
    id: str
    status: str  # active | ready
    # The next question to answer, or null when the backbone is exhausted.
    next_question: BriefStep | None
    content: BriefContent
