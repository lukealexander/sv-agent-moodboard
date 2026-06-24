/** The fixed stage backbone, plus the content the inputs draw on. */

import type { Stage, Step } from "./types";

export const STAGES: Stage[] = [
  { id: "work", title: "The work" },
  { id: "feeling", title: "The feeling" },
  { id: "references", title: "References" },
  { id: "palette", title: "Palette" },
  { id: "audience", title: "Audience" },
];

/** One primary step per stage. The agent may insert one adaptive follow-up within a stage. */
export const BACKBONE_STEPS: Step[] = [
  {
    id: "work",
    stageId: "work",
    kind: "text",
    prompt: "What are you making a moodboard for?",
    helper: "A project, a brand, a feeling — describe it in your own words.",
    forkable: true,
  },
  {
    id: "feeling",
    stageId: "feeling",
    kind: "chips",
    prompt: "How should it feel?",
    helper: "Pick the moods that fit, or add your own. A few is plenty.",
    seedChips: [
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
    forkable: true,
  },
  {
    id: "references",
    stageId: "references",
    kind: "references",
    prompt: "Bring in anything that inspires you.",
    helper: "Drop images here, paste from your clipboard, or browse. Optional.",
    forkable: false,
  },
  {
    id: "palette",
    stageId: "palette",
    kind: "palette",
    prompt: "Where does the colour sit?",
    helper: "Choose a few anchors, then dial the temperature and intensity.",
    forkable: true,
  },
  {
    id: "audience",
    stageId: "audience",
    kind: "text",
    prompt: "Who's it for, and where will it live?",
    helper: "Audience, context, medium — whatever matters most.",
    forkable: true,
  },
];

/** Selectable colour anchors for the palette picker. These are user content, not UI chrome. */
export interface Swatch {
  id: string;
  name: string;
  hex: string;
  /** rough position on the warm↔cool axis, for the agent's labelling. */
  warm: boolean;
}

export const SWATCHES: Swatch[] = [
  { id: "ember", name: "Ember", hex: "#C8643C", warm: true },
  { id: "amber", name: "Amber", hex: "#E0A33D", warm: true },
  { id: "clay", name: "Clay", hex: "#A8584A", warm: true },
  { id: "rose", name: "Rose", hex: "#C9577B", warm: true },
  { id: "sand", name: "Sand", hex: "#D8C6A0", warm: true },
  { id: "plum", name: "Plum", hex: "#6B3FA0", warm: false },
  { id: "indigo", name: "Indigo", hex: "#3F4DA0", warm: false },
  { id: "teal", name: "Teal", hex: "#2F9CB6", warm: false },
  { id: "sage", name: "Sage", hex: "#6FA079", warm: false },
  { id: "forest", name: "Forest", hex: "#2F6B4F", warm: false },
  { id: "slate", name: "Slate", hex: "#566173", warm: false },
  { id: "ivory", name: "Ivory", hex: "#EDE6D6", warm: true },
];

export interface PaletteAxis {
  id: "warmth" | "intensity";
  label: string;
  lowLabel: string;
  highLabel: string;
}

export const PALETTE_AXES: PaletteAxis[] = [
  { id: "warmth", label: "Temperature", lowLabel: "Cool", highLabel: "Warm" },
  { id: "intensity", label: "Intensity", lowLabel: "Muted", highLabel: "Vivid" },
];

export const swatchById = (id: string): Swatch | undefined =>
  SWATCHES.find((s) => s.id === id);
