import { BriefFlow } from "../features/brief/BriefFlow";
import styles from "./Brief.module.css";

/**
 * The moodboard brief flow. A deliberately light "studio" surface (it sets its own
 * background so it stays bright regardless of system theme); the dark, luminous
 * convergence is reserved for the generate/reveal moment.
 */
export function Brief() {
  return (
    <div className={styles.page}>
      <BriefFlow />
    </div>
  );
}
