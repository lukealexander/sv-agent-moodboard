import { useId } from "react";
import { AnswerInput } from "./inputs";
import { ArrowRightIcon, CloseIcon, ForkIcon, PlusIcon } from "./icons";
import type { Answer, AnswerValue, Step } from "./types";
import styles from "./QuestionPane.module.css";

interface QuestionPaneProps {
  step: Step;
  answer: Answer;
  thinking: boolean;
  isLastStep: boolean;
  canGenerateEarly: boolean;
  onChangeOption: (optionId: string, value: AnswerValue) => void;
  onAddFork: () => void;
  onRemoveFork: (optionId: string) => void;
  onContinue: () => void;
  onSkip: () => void;
  onGenerateNow: () => void;
}

const placeholderFor: Partial<Record<Step["stageId"], string>> = {
  work: "e.g. a rebrand for a neighbourhood coffee roaster…",
  audience: "e.g. design-literate regulars, mostly on mobile, in-store posters too…",
};

export function QuestionPane({
  step,
  answer,
  thinking,
  isLastStep,
  canGenerateEarly,
  onChangeOption,
  onAddFork,
  onRemoveFork,
  onContinue,
  onSkip,
  onGenerateNow,
}: QuestionPaneProps) {
  const headingId = useId();
  const forked = answer.options.length >= 2;
  const canFork = step.forkable && answer.options.length < 3;

  return (
    <section className={styles.pane} aria-busy={thinking}>
      <header className={styles.head}>
        <h2 id={headingId} className={styles.prompt}>
          {step.prompt}
        </h2>
        {step.helper && <p className={styles.helper}>{step.helper}</p>}
      </header>

      {thinking ? (
        <Thinking />
      ) : (
        <>
          <div className={styles.body} data-forked={forked}>
            {answer.options.map((option, i) => (
              <div key={option.id} className={styles.option} data-forked={forked}>
                {forked && (
                  <div className={styles.optionHead}>
                    <span className={styles.optionTag}>
                      <ForkIcon width={15} height={15} />
                      {i === 0 ? "This" : i === 1 ? "or that" : `or option ${String.fromCharCode(65 + i)}`}
                    </span>
                    {answer.options.length > 1 && (
                      <button
                        type="button"
                        className={styles.optionRemove}
                        onClick={() => onRemoveFork(option.id)}
                        aria-label={`Remove alternative ${String.fromCharCode(65 + i)}`}
                      >
                        <CloseIcon width={15} height={15} />
                      </button>
                    )}
                  </div>
                )}
                <AnswerInput
                  value={option.value}
                  seedChips={step.seedChips}
                  labelledBy={headingId}
                  autoFocus={i === 0 && step.kind === "text"}
                  placeholder={placeholderFor[step.stageId]}
                  onChange={(v) => onChangeOption(option.id, v)}
                />
              </div>
            ))}
          </div>

          {canFork && (
            <button type="button" className={styles.fork} onClick={onAddFork}>
              <PlusIcon width={16} height={16} />
              {forked ? "Add another alternative" : "…or explore an alternative"}
            </button>
          )}

          <footer className={styles.footer}>
            <button type="button" className={styles.skip} onClick={onSkip}>
              Not sure yet
            </button>
            <div className={styles.advance}>
              {canGenerateEarly && !isLastStep && (
                <button type="button" className={styles.generateNow} onClick={onGenerateNow}>
                  I've said enough
                </button>
              )}
              <button type="button" className={styles.continue} onClick={onContinue}>
                {isLastStep ? "Review directions" : "Continue"}
                <ArrowRightIcon width={18} height={18} />
              </button>
            </div>
          </footer>
        </>
      )}
    </section>
  );
}

function Thinking() {
  return (
    <div className={styles.thinking} role="status">
      <span className={styles.thinkingPulse} aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className={styles.thinkingLabel}>Thinking with you…</span>
    </div>
  );
}
