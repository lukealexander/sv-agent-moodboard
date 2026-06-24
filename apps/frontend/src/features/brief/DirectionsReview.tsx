import type { CSSProperties } from "react";
import { CloseIcon, ConvergeIcon, PlusIcon } from "./icons";
import type { DirectionPlan } from "./types";
import styles from "./DirectionsReview.module.css";

interface DirectionsReviewProps {
  plan: DirectionPlan;
  onRename: (id: string, name: string) => void;
  onRemove: (id: string) => void;
  onAdd: () => void;
  onGenerate: () => void;
  onBack: () => void;
}

const FACETS = [
  "var(--color-gold-dec)",
  "var(--color-teal-dec)",
  "var(--color-green-dec)",
  "var(--color-magenta-dec)",
];

export function DirectionsReview({
  plan,
  onRename,
  onRemove,
  onAdd,
  onGenerate,
  onBack,
}: DirectionsReviewProps) {
  const count = plan.directions.length;
  const single = count === 1;

  return (
    <section className={styles.review}>
      <header className={styles.head}>
        <h2 className={styles.title}>{single ? "Your brief is ready" : "Choose your directions"}</h2>
        <p className={styles.lede}>
          {single
            ? "I'll generate one moodboard from your brief. Add a direction to explore an alternative."
            : `I've shaped your brief into ${count} directions — same parts, arranged differently. Generate a moodboard for each, or refine them first.`}
        </p>
        {plan.note && (
          <p className={styles.note}>
            <ConvergeIcon width={16} height={16} />
            {plan.note}
          </p>
        )}
      </header>

      <ul className={styles.directions}>
        {plan.directions.map((dir, i) => (
          <li
            key={dir.id}
            className={styles.direction}
            style={{ "--facet": FACETS[i % FACETS.length] } as CSSProperties}
          >
            <div className={styles.dirHead}>
              <span className={styles.dirMark} aria-hidden="true" />
              <input
                className={styles.dirName}
                value={dir.name}
                aria-label={`Direction ${i + 1} name`}
                onChange={(e) => onRename(dir.id, e.target.value)}
              />
              {count > 1 && (
                <button
                  type="button"
                  className={styles.dirRemove}
                  onClick={() => onRemove(dir.id)}
                  aria-label={`Remove direction ${dir.name}`}
                >
                  <CloseIcon width={16} height={16} />
                </button>
              )}
            </div>
            {dir.highlights.length > 0 && (
              <ul className={styles.highlights}>
                {dir.highlights.map((h, j) => (
                  <li key={j}>{h}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>

      <button type="button" className={styles.add} onClick={onAdd}>
        <PlusIcon width={16} height={16} />
        Add a direction
      </button>

      <footer className={styles.footer}>
        <button type="button" className={styles.back} onClick={onBack}>
          Back to questions
        </button>
        <button type="button" className={styles.generate} onClick={onGenerate}>
          <ConvergeIcon width={18} height={18} />
          Generate {count} moodboard{count === 1 ? "" : "s"}
        </button>
      </footer>
    </section>
  );
}
