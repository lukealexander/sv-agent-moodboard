/** Small shared helpers for the moodboard brief flow. */

let counter = 0;

/** Monotonic, collision-resistant id for client-side objects (options, images, directions). */
export function uid(prefix = "id"): string {
  counter += 1;
  return `${prefix}-${counter.toString(36)}-${Date.now().toString(36)}`;
}

/** Promise-based delay; used by the mock agent to mimic real async latency. */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Clamp a number into [min, max]. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
