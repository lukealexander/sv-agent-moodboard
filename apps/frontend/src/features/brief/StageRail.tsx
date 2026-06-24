import { summarizeOption } from "./agent";
import { CheckIcon, ForkIcon, PencilIcon } from "./icons";
import type { StageProgress } from "./useBriefFlow";
import styles from "./StageRail.module.css";

interface StageRailProps {
  stages: StageProgress[];
  onRevisit: (stageId: string) => void;
}

export function StageRail({ stages, onRevisit }: StageRailProps) {
  return (
    <nav className={styles.rail} aria-label="Your brief so far">
      <p className={styles.heading}>Your brief</p>
      <ol className={styles.list}>
        {stages.map((stage) => {
          const summaries = stage.skipped
            ? []
            : stage.options
                .map((o) => summarizeOption(o))
                .filter((s) => s && s !== "—");
          const revisitable = stage.status === "done";
          const Tag = revisitable ? "button" : "div";

          return (
            <li key={stage.id} className={styles.item} data-status={stage.status}>
              <Tag
                className={styles.row}
                {...(revisitable
                  ? { type: "button", onClick: () => onRevisit(stage.id) }
                  : {})}
                aria-current={stage.status === "current" ? "step" : undefined}
              >
                <span className={styles.node} aria-hidden="true">
                  {stage.status === "done" && <CheckIcon width={13} height={13} />}
                </span>
                <span className={styles.content}>
                  <span className={styles.title}>
                    {stage.title}
                    {stage.forked && (
                      <span className={styles.forkTag}>
                        <ForkIcon width={13} height={13} />
                        {stage.options.length} ways
                      </span>
                    )}
                    {revisitable && <PencilIcon className={styles.pencil} width={14} height={14} />}
                  </span>

                  {stage.skipped && <span className={styles.skipped}>Skipped</span>}

                  {stage.status !== "upcoming" && summaries.length > 0 && (
                    <span className={styles.summaries}>
                      {summaries.map((s, i) => (
                        <span key={i} className={styles.summary}>
                          {stage.forked && (
                            <span className={styles.branchTag}>
                              {i === 0 ? "This" : "or"}
                            </span>
                          )}
                          {s}
                        </span>
                      ))}
                    </span>
                  )}
                </span>
              </Tag>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
