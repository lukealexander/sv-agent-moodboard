/**
 * Mock agent for the moodboard brief flow.
 *
 * STUB — no backend exists yet. Every function here mimics the real async behaviour
 * (latency, the possibility of failure) so the flow's thinking / loading / error states
 * are exercised for real. Swap each function for a `fetchWithAuth` call against the
 * moodboard endpoint when it lands; the call sites and return shapes stay the same.
 */

import { delay, uid } from "./helpers";
import { STAGES, swatchById } from "./stages";
import type {
  Answer,
  AnswerOption,
  Direction,
  DirectionPlan,
  Step,
} from "./types";

const MAX_DIRECTIONS = 4;

/** Test/preview seam: force the next generate() to fail, to exercise the error state. */
let simulateError = false;
export function setSimulateError(value: boolean): void {
  simulateError = value;
}

// Dev-only seam so tests/preview can exercise the generation error state. Tree-shaken in prod.
if (import.meta.env.DEV && typeof window !== "undefined") {
  (window as unknown as { __briefFailNext?: typeof setSimulateError }).__briefFailNext =
    setSimulateError;
}

const stageTitle = (stageId: string): string =>
  STAGES.find((s) => s.id === stageId)?.title ?? stageId;

/** One short, human phrase summarising a single answer option. */
export function summarizeOption(option: AnswerOption): string {
  const v = option.value;
  switch (v.kind) {
    case "text": {
      const words = v.text.trim().split(/\s+/).filter(Boolean);
      if (words.length === 0) return "—";
      return words.slice(0, 4).join(" ") + (words.length > 4 ? "…" : "");
    }
    case "chips":
      return v.chips.length ? v.chips.slice(0, 3).join(", ") : "—";
    case "references":
      return v.images.length
        ? `${v.images.length} reference${v.images.length === 1 ? "" : "s"}`
        : "—";
    case "palette": {
      // Untouched palette (no anchors, axes at the midpoint) carries no real answer yet.
      if (
        v.palette.swatches.length === 0 &&
        v.palette.warmth === 0.5 &&
        v.palette.intensity === 0.5
      ) {
        return "—";
      }
      const names = v.palette.swatches
        .map((id) => swatchById(id)?.name)
        .filter(Boolean) as string[];
      const temp = v.palette.warmth >= 0.6 ? "warm" : v.palette.warmth <= 0.4 ? "cool" : "balanced";
      const energy = v.palette.intensity >= 0.6 ? "vivid" : v.palette.intensity <= 0.4 ? "muted" : "even";
      const lead = names.length ? names.slice(0, 2).join(" + ") + ", " : "";
      return `${lead}${temp} · ${energy}`;
    }
  }
}

/** A compact name fragment for a forked branch, used when naming a direction. */
function branchTag(option: AnswerOption): string {
  const v = option.value;
  if (v.kind === "chips" && v.chips.length) return v.chips[0];
  if (v.kind === "palette") {
    if (v.palette.warmth >= 0.6) return "Warm";
    if (v.palette.warmth <= 0.4) return "Cool";
    return v.palette.intensity >= 0.6 ? "Vivid" : "Muted";
  }
  if (v.kind === "text" && v.text.trim()) {
    const w = v.text.trim().split(/\s+/)[0];
    return w.charAt(0).toUpperCase() + w.slice(1);
  }
  return "";
}

interface ForkEntry {
  step: Step;
  options: AnswerOption[];
}

/**
 * Adaptive follow-up: occasionally deepen a stage based on the answer.
 * Deterministic so the flow is predictable; at most one follow-up per stage (enforced
 * by the caller). Returns null when the agent has nothing useful to ask.
 */
export async function proposeFollowUp(
  step: Step,
  answer: Answer,
): Promise<Step | null> {
  await delay(650);
  if (answer.skipped) return null;

  // Read the chips from the first option (the primary branch).
  const chips =
    answer.options[0]?.value.kind === "chips"
      ? (answer.options[0].value as { kind: "chips"; chips: string[] }).chips
      : [];

  if (step.stageId === "feeling") {
    if (chips.includes("Calm")) {
      return followUpStep("feeling", "What kind of calm?", [
        "Spa-calm",
        "Minimalist-calm",
        "Natural-calm",
        "Nocturnal-calm",
      ]);
    }
    if (chips.includes("Bold")) {
      return followUpStep("feeling", "Bold in which way?", [
        "Loud colour",
        "Oversized type",
        "High contrast",
        "Unexpected pairings",
      ]);
    }
    if (chips.includes("Editorial")) {
      return followUpStep("feeling", "What's the editorial reference?", [
        "Fashion glossy",
        "Independent zine",
        "Broadsheet",
        "Art-book",
      ]);
    }
  }
  return null;
}

function followUpStep(
  stageId: Step["stageId"],
  prompt: string,
  chips: string[],
): Step {
  return {
    id: uid("follow"),
    stageId,
    kind: "chips",
    prompt,
    helper: "A quick refinement — pick what fits, or move on.",
    seedChips: chips,
    forkable: true,
    adaptive: true,
  };
}

/**
 * Curate a small set of coherent directions from the forks.
 * Never the naive cartesian product: capped at MAX_DIRECTIONS, and when there are more
 * possible combinations than that, the surplus is summarised in `note` (no silent drop).
 */
export async function composeDirections(
  steps: Step[],
  answers: Record<string, Answer>,
): Promise<DirectionPlan> {
  await delay(900);

  const forks: ForkEntry[] = steps
    .map((step) => ({ step, answer: answers[step.id] }))
    .filter(
      (e): e is { step: Step; answer: Answer } =>
        !!e.answer && !e.answer.skipped && e.answer.options.length >= 2,
    )
    .map((e) => ({ step: e.step, options: e.answer.options }));

  // No divergence → a single direction built from the whole brief.
  if (forks.length === 0) {
    const highlights = settledHighlights(steps, answers);
    return {
      directions: [{ id: uid("dir"), name: "Your brief", picks: {}, highlights }],
      note: null,
    };
  }

  // All combinations of one option per forked step.
  let combos: Record<string, string>[] = [{}];
  for (const fork of forks) {
    const next: Record<string, string>[] = [];
    for (const combo of combos) {
      for (const option of fork.options) {
        next.push({ ...combo, [fork.step.id]: option.id });
      }
    }
    combos = next;
  }

  const total = combos.length;
  let chosen = combos;
  let note: string | null = null;

  if (total > MAX_DIRECTIONS) {
    // Curate to a diverse trio: the two "pure" extremes plus one balanced mix.
    const first = forks.reduce<Record<string, string>>((acc, f) => {
      acc[f.step.id] = f.options[0].id;
      return acc;
    }, {});
    const last = forks.reduce<Record<string, string>>((acc, f) => {
      acc[f.step.id] = f.options[f.options.length - 1].id;
      return acc;
    }, {});
    const mixed = forks.reduce<Record<string, string>>((acc, f, i) => {
      acc[f.step.id] = f.options[i % f.options.length].id;
      return acc;
    }, {});
    chosen = dedupePicks([first, mixed, last]);
    note = `${total} combinations were possible — I've focused them into ${chosen.length} distinct directions.`;
  }

  const directions: Direction[] = chosen.map((picks, i) =>
    buildDirection(picks, forks, i),
  );
  return { directions, note };
}

function dedupePicks(picks: Record<string, string>[]): Record<string, string>[] {
  const seen = new Set<string>();
  const out: Record<string, string>[] = [];
  for (const p of picks) {
    const key = JSON.stringify(p);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(p);
    }
  }
  return out;
}

function buildDirection(
  picks: Record<string, string>,
  forks: ForkEntry[],
  index: number,
): Direction {
  const tags: string[] = [];
  const highlights: string[] = [];
  for (const fork of forks) {
    const option = fork.options.find((o) => o.id === picks[fork.step.id]);
    if (!option) continue;
    const tag = branchTag(option);
    if (tag) tags.push(tag);
    highlights.push(`${stageTitle(fork.step.stageId)}: ${summarizeOption(option)}`);
  }
  const name = tags.slice(0, 2).join(" · ") || `Direction ${String.fromCharCode(65 + index)}`;
  return { id: uid("dir"), name, picks, highlights };
}

/** Distinctive lines from the settled (non-forked) answers, for the single-direction case. */
function settledHighlights(
  steps: Step[],
  answers: Record<string, Answer>,
): string[] {
  const lines: string[] = [];
  for (const step of steps) {
    const answer = answers[step.id];
    if (!answer || answer.skipped || !answer.options[0]) continue;
    const summary = summarizeOption(answer.options[0]);
    if (summary && summary !== "—") {
      lines.push(`${stageTitle(step.stageId)}: ${summary}`);
    }
  }
  return lines.slice(0, 5);
}

/**
 * Generate the moodboards. Resolves after the convergence reveal has had time to play.
 * The board *result* view is a separate surface; this resolves the handoff.
 */
export async function generate(directions: Direction[]): Promise<Direction[]> {
  await delay(2600);
  if (simulateError) {
    throw new Error("The studio couldn't resolve your directions just now.");
  }
  return directions;
}
