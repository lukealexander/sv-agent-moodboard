"""Generation API schemas."""

from pydantic import BaseModel, Field, model_validator


class StandaloneBrief(BaseModel):
    """A brief supplied inline, for callers that skip the guided briefing entirely."""

    prompt: str  # what the moodboard is for / the creative vision, in words
    directions: list[str] | None = None  # explicit divergent directions to render
    palette_hint: list[str] | None = None  # optional hex anchors
    references: list[str] | None = None  # optional reference image URLs or notes


class GenerateRequest(BaseModel):
    """Start generation from EITHER a saved brief session or an inline brief.

    The two paths are mutually exclusive — exactly one of ``brief_id`` / ``brief``.
    """

    brief_id: str | None = None
    brief: StandaloneBrief | None = None
    # Which directions to render, by name. Omit to use every direction the brief
    # carries (or a single default when it has none).
    directions: list[str] | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "GenerateRequest":
        if bool(self.brief_id) == bool(self.brief):
            raise ValueError("provide exactly one of `brief_id` or `brief`")
        return self


class ImageRef(BaseModel):
    index: int
    url: str | None = None  # storage URL (S3) or API asset path; null until rendered
    prompt: str
    alt: str


class MoodboardResponse(BaseModel):
    id: str
    request_id: str
    direction_name: str
    status: str  # queued | composing | rendering | assembling | done | error
    concept: dict | None = None
    palette: list[dict] | None = None
    images: list[ImageRef] = Field(default_factory=list)
    html_url: str | None = None
    error: str | None = None


class MoodboardSummary(BaseModel):
    id: str
    direction_name: str
    status: str


class GenerationRequestResponse(BaseModel):
    id: str
    status: str  # queued | running | done | partial | error
    brief_id: str | None = None
    moodboards: list[MoodboardSummary] = Field(default_factory=list)
    error: str | None = None
