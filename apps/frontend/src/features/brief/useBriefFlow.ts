/**
 * The brief flow's state machine.
 *
 * The reducer is pure; all agent calls (which are async and may fail) live in the
 * action callbacks the hook returns. Status transitions:
 *   answering → thinking → (answering | directions) → generating → (revealed | error)
 */

import { useCallback, useMemo, useReducer } from "react";
import { composeDirections, generate, proposeFollowUp } from "./agent";
import { uid } from "./helpers";
import { BACKBONE_STEPS, STAGES } from "./stages";
import type {
  Answer,
  AnswerValue,
  Direction,
  DirectionPlan,
  FlowStatus,
  InputKind,
  StageId,
  Step,
} from "./types";

interface FlowState {
  steps: Step[];
  answers: Record<string, Answer>;
  cursor: number;
  status: FlowStatus;
  /** stages whose follow-up decision has already been made (cap of one follow-up each). */
  processedStages: StageId[];
  plan: DirectionPlan | null;
  error: string | null;
}

type Action =
  | { type: "setOption"; stepId: string; optionId: string; value: AnswerValue }
  | { type: "addFork"; stepId: string }
  | { type: "removeFork"; stepId: string; optionId: string }
  | { type: "setSkipped"; stepId: string; skipped: boolean }
  | { type: "insertFollowUp"; step: Step }
  | { type: "markProcessed"; stageId: StageId }
  | { type: "goto"; index: number }
  | { type: "status"; status: FlowStatus }
  | { type: "plan"; plan: DirectionPlan }
  | { type: "renameDirection"; id: string; name: string }
  | { type: "removeDirection"; id: string }
  | { type: "addDirection" }
  | { type: "error"; error: string | null }
  | { type: "reset" };

function emptyValue(kind: InputKind): AnswerValue {
  switch (kind) {
    case "text":
      return { kind: "text", text: "" };
    case "chips":
      return { kind: "chips", chips: [] };
    case "references":
      return { kind: "references", images: [] };
    case "palette":
      return { kind: "palette", palette: { swatches: [], warmth: 0.5, intensity: 0.5 } };
  }
}

function makeAnswer(step: Step): Answer {
  return {
    stepId: step.id,
    options: [{ id: uid("opt"), value: emptyValue(step.kind) }],
    skipped: false,
  };
}

export function isOptionEmpty(value: AnswerValue): boolean {
  switch (value.kind) {
    case "text":
      return value.text.trim() === "";
    case "chips":
      return value.chips.length === 0;
    case "references":
      return value.images.length === 0;
    case "palette":
      return value.palette.swatches.length === 0;
  }
}

function init(): FlowState {
  const answers: Record<string, Answer> = {};
  for (const step of BACKBONE_STEPS) answers[step.id] = makeAnswer(step);
  return {
    steps: BACKBONE_STEPS,
    answers,
    cursor: 0,
    status: "answering",
    processedStages: [],
    plan: null,
    error: null,
  };
}

function reducer(state: FlowState, action: Action): FlowState {
  switch (action.type) {
    case "setOption": {
      const answer = state.answers[action.stepId];
      if (!answer) return state;
      const options = answer.options.map((o) =>
        o.id === action.optionId ? { ...o, value: action.value } : o,
      );
      return {
        ...state,
        answers: {
          ...state.answers,
          [action.stepId]: { ...answer, options, skipped: false },
        },
      };
    }
    case "addFork": {
      const answer = state.answers[action.stepId];
      const step = state.steps.find((s) => s.id === action.stepId);
      if (!answer || !step || answer.options.length >= 3) return state;
      return {
        ...state,
        answers: {
          ...state.answers,
          [action.stepId]: {
            ...answer,
            skipped: false,
            options: [
              ...answer.options,
              { id: uid("opt"), value: emptyValue(step.kind) },
            ],
          },
        },
      };
    }
    case "removeFork": {
      const answer = state.answers[action.stepId];
      if (!answer || answer.options.length <= 1) return state;
      return {
        ...state,
        answers: {
          ...state.answers,
          [action.stepId]: {
            ...answer,
            options: answer.options.filter((o) => o.id !== action.optionId),
          },
        },
      };
    }
    case "setSkipped": {
      const answer = state.answers[action.stepId];
      if (!answer) return state;
      return {
        ...state,
        answers: {
          ...state.answers,
          [action.stepId]: { ...answer, skipped: action.skipped },
        },
      };
    }
    case "insertFollowUp": {
      const steps = [...state.steps];
      steps.splice(state.cursor + 1, 0, action.step);
      return {
        ...state,
        steps,
        answers: { ...state.answers, [action.step.id]: makeAnswer(action.step) },
        processedStages: state.processedStages.includes(action.step.stageId)
          ? state.processedStages
          : [...state.processedStages, action.step.stageId],
        cursor: state.cursor + 1,
        status: "answering",
      };
    }
    case "markProcessed":
      return state.processedStages.includes(action.stageId)
        ? state
        : { ...state, processedStages: [...state.processedStages, action.stageId] };
    case "goto":
      return { ...state, cursor: action.index, status: "answering" };
    case "status":
      return { ...state, status: action.status };
    case "plan":
      return { ...state, plan: action.plan, status: "directions", error: null };
    case "renameDirection": {
      if (!state.plan) return state;
      return {
        ...state,
        plan: {
          ...state.plan,
          directions: state.plan.directions.map((d) =>
            d.id === action.id ? { ...d, name: action.name } : d,
          ),
        },
      };
    }
    case "removeDirection": {
      if (!state.plan || state.plan.directions.length <= 1) return state;
      return {
        ...state,
        plan: {
          ...state.plan,
          directions: state.plan.directions.filter((d) => d.id !== action.id),
        },
      };
    }
    case "addDirection": {
      if (!state.plan) return state;
      const seed = state.plan.directions[0];
      const next: Direction = {
        id: uid("dir"),
        name: "New direction",
        picks: seed ? { ...seed.picks } : {},
        highlights: seed ? [...seed.highlights] : [],
      };
      return {
        ...state,
        plan: { ...state.plan, directions: [...state.plan.directions, next] },
      };
    }
    case "error":
      return { ...state, error: action.error, status: action.error ? "error" : state.status };
    case "reset":
      return init();
  }
}

const stageOf = (steps: Step[], stageId: StageId) => {
  const indices = steps.flatMap((s, i) => (s.stageId === stageId ? [i] : []));
  return { first: indices[0] ?? -1, last: indices[indices.length - 1] ?? -1 };
};

export interface StageProgress {
  id: StageId;
  title: string;
  status: "done" | "current" | "upcoming";
  /** backbone-step option summaries; rendered in the rail. */
  options: { id: string; value: AnswerValue }[];
  forked: boolean;
  skipped: boolean;
}

export function useBriefFlow() {
  const [state, dispatch] = useReducer(reducer, undefined, init);
  const { steps, answers, cursor, status, plan, error } = state;

  const currentStep = steps[cursor];
  const currentAnswer = currentStep ? answers[currentStep.id] : undefined;

  const setOption = useCallback(
    (stepId: string, optionId: string, value: AnswerValue) =>
      dispatch({ type: "setOption", stepId, optionId, value }),
    [],
  );
  const addFork = useCallback((stepId: string) => dispatch({ type: "addFork", stepId }), []);
  const removeFork = useCallback(
    (stepId: string, optionId: string) => dispatch({ type: "removeFork", stepId, optionId }),
    [],
  );
  const goTo = useCallback((index: number) => dispatch({ type: "goto", index }), []);

  /** Compose directions from the current answers (used at the end and by "Generate now"). */
  const finish = useCallback(async () => {
    dispatch({ type: "status", status: "thinking" });
    const result = await composeDirections(state.steps, state.answers);
    dispatch({ type: "plan", plan: result });
  }, [state.steps, state.answers]);

  /** Advance from the current step: maybe insert a follow-up, else move on or finish. */
  const advance = useCallback(async () => {
    const step = state.steps[state.cursor];
    if (!step) return;
    const answer = state.answers[step.id];

    if (!step.adaptive && !state.processedStages.includes(step.stageId)) {
      if (answer && !answer.skipped && !answer.options.every((o) => isOptionEmpty(o.value))) {
        dispatch({ type: "status", status: "thinking" });
        const follow = await proposeFollowUp(step, answer);
        if (follow) {
          dispatch({ type: "insertFollowUp", step: follow });
          return;
        }
      }
      dispatch({ type: "markProcessed", stageId: step.stageId });
    }

    if (state.cursor < state.steps.length - 1) {
      dispatch({ type: "goto", index: state.cursor + 1 });
      return;
    }
    await finish();
  }, [state.steps, state.cursor, state.answers, state.processedStages, finish]);

  const skipStep = useCallback(() => {
    if (!currentStep) return;
    dispatch({ type: "setSkipped", stepId: currentStep.id, skipped: true });
    // advance on the next tick so the skipped flag is committed first
    setTimeout(() => void advance(), 0);
  }, [currentStep, advance]);

  const runGenerate = useCallback(async () => {
    if (!state.plan) return;
    dispatch({ type: "status", status: "generating" });
    dispatch({ type: "error", error: null });
    try {
      await generate(state.plan.directions);
      dispatch({ type: "status", status: "revealed" });
    } catch (e) {
      dispatch({ type: "error", error: e instanceof Error ? e.message : "Generation failed." });
    }
  }, [state.plan]);

  const stageProgress: StageProgress[] = useMemo(
    () =>
      STAGES.map((stage) => {
        const { first, last } = stageOf(steps, stage.id);
        const status: StageProgress["status"] =
          first === -1
            ? "upcoming"
            : cursor > last
              ? "done"
              : cursor >= first
                ? "current"
                : "upcoming";
        const answer = answers[stage.id];
        return {
          id: stage.id,
          title: stage.title,
          status,
          options: answer ? answer.options : [],
          forked: !!answer && answer.options.length >= 2,
          skipped: !!answer && answer.skipped,
        };
      }),
    [steps, answers, cursor],
  );

  const stepNumber = cursor + 1;
  const stepCount = steps.length;
  const canGenerateEarly = useMemo(
    () =>
      cursor > 0 ||
      (!!currentAnswer && !currentAnswer.options.every((o) => isOptionEmpty(o.value))),
    [cursor, currentAnswer],
  );

  return {
    steps,
    answers,
    cursor,
    status,
    plan,
    error,
    currentStep,
    currentAnswer,
    stageProgress,
    stepNumber,
    stepCount,
    canGenerateEarly,
    setOption,
    addFork,
    removeFork,
    skipStep,
    advance,
    goTo,
    finish,
    runGenerate,
    renameDirection: useCallback(
      (id: string, name: string) => dispatch({ type: "renameDirection", id, name }),
      [],
    ),
    removeDirection: useCallback((id: string) => dispatch({ type: "removeDirection", id }), []),
    addDirection: useCallback(() => dispatch({ type: "addDirection" }), []),
    backToQuestions: useCallback(
      () => dispatch({ type: "goto", index: state.steps.length - 1 }),
      [state.steps.length],
    ),
    reset: useCallback(() => dispatch({ type: "reset" }), []),
  };
}
