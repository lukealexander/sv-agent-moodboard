"""Briefing orchestration — walk the stage backbone, insert adaptive follow-ups, and
curate directions. Pure functions over ``BriefContent``; persistence lives in the router.
"""

from app.ids import uid
from app.providers.llm import LLMProvider
from app.schemas.brief import (
    Answer,
    AnswerOption,
    AnswerRequest,
    BriefContent,
    BriefStep,
    ChipsValue,
)
from app.services import directions as directions_svc
from app.services.stages import backbone_steps


def new_content() -> BriefContent:
    return BriefContent(steps=backbone_steps(), answers={}, processed_stages=[])


def current_question(content: BriefContent) -> BriefStep | None:
    """The first step that hasn't been answered yet — what the client answers next."""
    for step in content.steps:
        if step.id not in content.answers:
            return step
    return None


def _answer_from_request(step: BriefStep, req: AnswerRequest) -> Answer:
    if req.skip:
        return Answer(step_id=step.id, options=[], skipped=True)
    if req.options:
        return Answer(
            step_id=step.id,
            options=[AnswerOption(id=uid("opt"), value=v) for v in req.options],
        )
    if req.value is not None:
        return Answer(step_id=step.id, options=[AnswerOption(id=uid("opt"), value=req.value)])
    # Nothing provided — treat as a skip rather than erroring.
    return Answer(step_id=step.id, options=[], skipped=True)


async def submit_answer(
    content: BriefContent, llm: LLMProvider, req: AnswerRequest
) -> BriefContent:
    """Record an answer to the current step and advance — possibly inserting one
    agent follow-up within the stage. Raises ``ValueError`` if the brief is complete."""
    step = current_question(content)
    if step is None:
        raise ValueError("brief is already complete")

    answer = _answer_from_request(step, req)
    content.answers[step.id] = answer

    if not step.adaptive and step.stage not in content.processed_stages:
        await _maybe_followup(content, llm, step, answer)
        content.processed_stages.append(step.stage)

    return content


async def _maybe_followup(
    content: BriefContent, llm: LLMProvider, step: BriefStep, answer: Answer
) -> None:
    # Only chips stages get a refining follow-up, and only with real content.
    if step.kind != "chips" or answer.skipped or not answer.options:
        return
    primary = answer.options[0].value
    if not isinstance(primary, ChipsValue) or not primary.chips:
        return
    followup = await llm.propose_followup(step.stage, primary.chips)
    if followup is None:
        return
    new_step = BriefStep(
        id=uid("follow"),
        stage=step.stage,
        kind="chips",
        prompt=followup.prompt,
        helper="A quick refinement — pick what fits, or move on.",
        seed_chips=followup.chips,
        forkable=True,
        adaptive=True,
    )
    index = content.steps.index(step)
    content.steps.insert(index + 1, new_step)


def compose_directions(content: BriefContent) -> BriefContent:
    """Curate divergent directions from the forks (deterministic)."""
    directions, note = directions_svc.compose_directions(content)
    content.directions = directions
    content.note = note
    return content
