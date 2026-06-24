/**
 * Domain types for the multi-step moodboard brief flow.
 *
 * Model: the user walks a fixed backbone of named STAGES. Each stage carries one or
 * more STEPS (a question + an input). Within a stage the agent may insert one adaptive
 * follow-up step. Any forkable answer can hold more than one OPTION ("this … or that");
 * an answer with ≥2 options is a fork. Before generation the agent curates a small set
 * of DIRECTIONS from the forks — one moodboard variant per direction.
 */

export type StageId = "work" | "feeling" | "references" | "palette" | "audience";

export type InputKind = "text" | "chips" | "references" | "palette";

/** One image the user dropped, pasted, or browsed in. `src` is an object URL for preview. */
export interface ReferenceImage {
  id: string;
  name: string;
  src: string;
}

/** A palette answer: anchor swatches plus where it sits on two axes. */
export interface PaletteValue {
  /** ids of selected swatches (see SWATCHES in stages.ts). */
  swatches: string[];
  /** 0 = cool … 1 = warm. */
  warmth: number;
  /** 0 = muted … 1 = vivid. */
  intensity: number;
}

/** The value of a single answer option, discriminated by input kind. */
export type AnswerValue =
  | { kind: "text"; text: string }
  | { kind: "chips"; chips: string[] }
  | { kind: "references"; images: ReferenceImage[] }
  | { kind: "palette"; palette: PaletteValue };

/** One branch of a (possibly forked) answer. */
export interface AnswerOption {
  id: string;
  value: AnswerValue;
}

/** A question with an input. Backbone steps are fixed; `adaptive` steps are agent follow-ups. */
export interface Step {
  id: string;
  stageId: StageId;
  kind: InputKind;
  prompt: string;
  helper?: string;
  /** chips kind: starter suggestions the user can pick or extend. */
  seedChips?: string[];
  /** whether the answer to this step may diverge into alternatives. */
  forkable: boolean;
  /** true when the agent inserted this step in response to an answer. */
  adaptive?: boolean;
}

/** The user's answer to one step. `options.length === 1` is settled; `>= 2` is a fork. */
export interface Answer {
  stepId: string;
  options: AnswerOption[];
  skipped: boolean;
}

export interface Stage {
  id: StageId;
  /** short title shown in the rail and as the step's stage tag. */
  title: string;
}

export type FlowStatus =
  | "answering" // a question is shown, awaiting input
  | "thinking" // agent computing a follow-up or composing directions
  | "directions" // reviewing the curated directions
  | "generating" // the dark convergence reveal is running
  | "revealed" // generation handoff complete (result view is a separate surface)
  | "error"; // generation failed

/** A curated divergent direction. `picks` maps each forked stepId → the chosen option id. */
export interface Direction {
  id: string;
  name: string;
  picks: Record<string, string>;
  /** one short line per distinctive choice, for the review card. */
  highlights: string[];
}

/** Result of curating directions from the forks. */
export interface DirectionPlan {
  directions: Direction[];
  /** set when combinations were curated down, so nothing is silently dropped. */
  note: string | null;
}
