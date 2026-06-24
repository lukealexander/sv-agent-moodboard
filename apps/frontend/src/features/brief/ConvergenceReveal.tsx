import type { CSSProperties } from "react";
import { ArrowRightIcon, ConvergeIcon } from "./icons";
import type { Direction } from "./types";
import styles from "./ConvergenceReveal.module.css";

interface ConvergenceRevealProps {
  status: "generating" | "revealed" | "error";
  directions: Direction[];
  error: string | null;
  onRetry: () => void;
  onBack: () => void;
  onReset: () => void;
}

/** The four facets orbit the spark. Start offsets (px) + stagger; CSS animates the converge. */
const ORBS = [
  { facet: "var(--color-gold-on-dark)", tx: -128, ty: -86, delay: 0 },
  { facet: "var(--color-teal-on-dark)", tx: 132, ty: -72, delay: 140 },
  { facet: "var(--color-green-on-dark)", tx: -112, ty: 104, delay: 280 },
  { facet: "var(--color-magenta-on-dark)", tx: 120, ty: 110, delay: 420 },
];

const FACET_PILLS = [
  "var(--color-gold-on-dark)",
  "var(--color-teal-on-dark)",
  "var(--color-green-on-dark)",
  "var(--color-magenta-on-dark)",
];

export function ConvergenceReveal({
  status,
  directions,
  error,
  onRetry,
  onBack,
  onReset,
}: ConvergenceRevealProps) {
  const count = directions.length;

  return (
    <div className={styles.stage} data-status={status} role={status === "error" ? "alert" : "status"}>
      <div className={styles.field} aria-hidden="true">
        {ORBS.map((orb, i) => (
          <span
            key={i}
            className={styles.orb}
            style={
              {
                "--facet": orb.facet,
                "--tx": `${orb.tx}px`,
                "--ty": `${orb.ty}px`,
                "--delay": `${orb.delay}ms`,
              } as CSSProperties
            }
          />
        ))}
        <span className={styles.spark} />
      </div>

      {status === "generating" && (
        <div className={styles.caption}>
          <h2 className={styles.captionTitle} aria-live="polite">
            {count === 1 ? "Resolving your moodboard" : `Resolving your ${count} directions`}
          </h2>
          <p className={styles.captionSub}>Arranging the facets into a whole.</p>
        </div>
      )}

      {status === "revealed" && (
        <div className={styles.caption}>
          <h2 className={styles.captionTitle}>
            {count === 1 ? "Your moodboard has resolved" : "Your directions have resolved"}
          </h2>
          <ul className={styles.pills}>
            {directions.map((dir, i) => (
              <li
                key={dir.id}
                className={styles.pill}
                style={{ "--facet": FACET_PILLS[i % FACET_PILLS.length] } as CSSProperties}
              >
                <span className={styles.pillDot} aria-hidden="true" />
                {dir.name}
              </li>
            ))}
          </ul>
          <p className={styles.captionSub}>The boards open on the next surface.</p>
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={onReset}>
              Start another brief
              <ArrowRightIcon width={18} height={18} />
            </button>
            <button type="button" className={styles.ghost} onClick={onBack}>
              Refine directions
            </button>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className={styles.caption}>
          <h2 className={styles.captionTitle}>That didn't resolve</h2>
          <p className={styles.captionSub}>
            {error ?? "Something interrupted the studio."} Nothing's lost — your brief and directions
            are intact.
          </p>
          <div className={styles.actions}>
            <button type="button" className={styles.primary} onClick={onRetry}>
              <ConvergeIcon width={18} height={18} />
              Try again
            </button>
            <button type="button" className={styles.ghost} onClick={onBack}>
              Refine directions
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
