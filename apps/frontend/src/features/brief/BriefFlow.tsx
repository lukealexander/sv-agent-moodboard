import { Link } from "react-router-dom";
import { ConvergenceReveal } from "./ConvergenceReveal";
import { DirectionsReview } from "./DirectionsReview";
import { QuestionPane } from "./QuestionPane";
import { StageRail } from "./StageRail";
import { useBriefFlow } from "./useBriefFlow";
import styles from "./BriefFlow.module.css";

export function BriefFlow() {
  const flow = useBriefFlow();
  const {
    steps,
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
    renameDirection,
    removeDirection,
    addDirection,
    backToQuestions,
    reset,
  } = flow;

  const revisit = (stageId: string) => {
    const index = steps.findIndex((s) => s.stageId === stageId);
    if (index >= 0) goTo(index);
  };

  // The dark convergence takes over the viewport for generate / reveal / error.
  if (status === "generating" || status === "revealed" || status === "error") {
    return (
      <ConvergenceReveal
        status={status}
        directions={plan?.directions ?? []}
        error={error}
        onRetry={runGenerate}
        onBack={backToQuestions}
        onReset={reset}
      />
    );
  }

  const isLastStep = currentStep ? steps.indexOf(currentStep) === steps.length - 1 : false;
  const onFirstStep = currentStep ? steps.indexOf(currentStep) === 0 : false;

  return (
    <div className={styles.flow}>
      <header className={styles.header}>
        <Link to="/" className={styles.wordmark}>
          Agent Moodboard
        </Link>
        {status !== "directions" && (
          <span className={styles.counter}>
            Step {stepNumber} of {stepCount}
          </span>
        )}
      </header>

      <div className={styles.body}>
        <aside className={styles.railZone}>
          <StageRail stages={stageProgress} onRevisit={revisit} />
        </aside>

        <main className={styles.main}>
          {status === "directions" && plan ? (
            <DirectionsReview
              plan={plan}
              onRename={renameDirection}
              onRemove={removeDirection}
              onAdd={addDirection}
              onGenerate={runGenerate}
              onBack={backToQuestions}
            />
          ) : (
            currentStep &&
            currentAnswer && (
              <>
                {onFirstStep && status === "answering" && (
                  <div className={styles.intro}>
                    <h1 className={styles.introTitle}>Let's build a moodboard</h1>
                    <p className={styles.introLede}>
                      A few questions, answered loosely. Where you're torn, keep both — we can
                      explore more than one direction.
                    </p>
                  </div>
                )}
                <QuestionPane
                  key={currentStep.id}
                  step={currentStep}
                  answer={currentAnswer}
                  thinking={status === "thinking"}
                  isLastStep={isLastStep}
                  canGenerateEarly={canGenerateEarly}
                  onChangeOption={(optionId, value) => setOption(currentStep.id, optionId, value)}
                  onAddFork={() => addFork(currentStep.id)}
                  onRemoveFork={(optionId) => removeFork(currentStep.id, optionId)}
                  onContinue={advance}
                  onSkip={skipStep}
                  onGenerateNow={finish}
                />
              </>
            )
          )}
        </main>
      </div>
    </div>
  );
}
