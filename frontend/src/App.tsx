import { useEffect, useRef, useState } from "react";
import { StartScreen } from "./components/Shell/StartScreen";
import { TopBar } from "./components/Shell/TopBar";
import { TryAnother } from "./components/Shell/TryAnother";
import { ProvenanceHint } from "./components/Shell/ProvenanceHint";
import { HistoryDrawer } from "./components/Shell/HistoryDrawer";
import { Banner } from "./components/Shell/Banner";
import { DeckPlaceholder } from "./components/Bench/DeckPlaceholder";
import { Deck } from "./components/Bench/Deck";
import { RevealStage } from "./components/Shell/RevealStage";
import { StageStrip } from "./components/Shell/StageStrip";
import { TopicSection } from "./components/Topic/TopicSection";
import { NeighborList } from "./components/Topic/NeighborList";
import { DesignSection } from "./components/Design/DesignSection";
import { ReviewThread } from "./components/Review/ReviewThread";
import { RobotSection } from "./components/Robot/RobotSection";
import { UncertaintySection } from "./components/Uncertainty/UncertaintySection";
import { LabControls } from "./components/Controls/LabControls";
import { useRun } from "./hooks/useRun";
import { useHealth } from "./api/queries";
import { loadRecordedIndex, type RecordedIndexEntry } from "./api/recorded";
import { gateOk } from "./api/normalize";
import { pushHistory } from "./lib/history";
import { applyWhatIf } from "./lib/whatif";
import { useUIStore } from "./state/store";
import { useWhatIf } from "./hooks/useWhatIf";
import { FeedbackCard } from "./components/Feedback/FeedbackCard";
import styles from "./App.module.css";

export function App() {
  const {
    run,
    origin,
    start,
    openRecorded,
    openRunId,
    isRunning,
    error,
    setRun,
  } = useRun();
  const health = useHealth();
  const question = useUIStore((s) => s.question);
  const setQuestion = useUIStore((s) => s.setQuestion);
  const loadRun = useUIStore((s) => s.loadRun);
  const clearActive = useUIStore((s) => s.clearActive);
  const active = useUIStore((s) => s.active);
  const whatIf = useWhatIf();
  const [recorded, setRecorded] = useState<RecordedIndexEntry[]>([]);
  const [shared, setShared] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadRecordedIndex().then(setRecorded);
  }, []);

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const runId = p.get("run");
    const demo = p.get("demo");
    if (runId) openRunId(runId);
    else if (demo) openRecorded(demo);
  }, [openRunId, openRecorded]);

  const serverDown = health.isError;
  const topic = run?.topic ?? null;
  const blocked = run?.blocked || (topic != null && !gateOk(topic.safety));

  // W1.3: one active design/report/sim for the whole screen. Seeded from the run; replaced
  // by what-if results. The notebook and the bench both read from it.
  useEffect(() => {
    if (run && !blocked) loadRun(run);
  }, [run, blocked, loadRun]);

  const design = active?.baseDesign ?? run?.design ?? null;
  const activeDesignVal = active
    ? applyWhatIf(active.baseDesign, active.patch).design
    : design;
  const report = active?.report ?? run?.uncertainty ?? null;
  const sim = active?.sim ?? run?.sim ?? null;

  useEffect(() => {
    if (run && topic && !blocked && run.uncertainty) {
      pushHistory({
        runId: run.run_id,
        question: topic.query,
        topicName: topic.topic.name,
        viability: topic.matrix.total,
        p90: run.uncertainty.fold_error.p90,
        at: Date.now(),
      });
    }
  }, [run, topic, blocked]);

  // A new run has arrived: scroll the notebook back to the top and flash a short confirmation.
  const lastRunId = useRef<string | null>(null);
  useEffect(() => {
    if (run && run.run_id !== lastRunId.current) {
      lastRunId.current = run.run_id;
      scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      window.scrollTo({ top: 0, behavior: "smooth" });
      if (topic) {
        setToast(`Now showing ${topic.topic.name}`);
        const t = setTimeout(() => setToast(null), 2600);
        return () => clearTimeout(t);
      }
    }
  }, [run, topic]);

  const runQuestion = (q: string) => {
    setQuestion(q);
    start(q);
  };
  const pivot = (name: string) => runQuestion(name);

  // Apply a feedback recommendation as a what-if (sets the draft and runs the server call).
  const applyFeedback = (patch: { top_nM?: number; factor?: number; points?: number; replicates?: number }) => {
    whatIf.setPatch({ ...whatIf.patch, ...patch });
    whatIf.commit();
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const newQuestion = () => {
    setRun(null);
    clearActive();
    setQuestion("");
    setToast(null);
    lastRunId.current = null;
    window.history.replaceState(null, "", window.location.pathname);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const share = () => {
    if (!run) return;
    const url = `${window.location.origin}${window.location.pathname}?run=${run.run_id}`;
    navigator.clipboard?.writeText(url).then(() => {
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    });
  };

  const status =
    origin === "recorded"
      ? "Recorded run"
      : serverDown
        ? "Can't reach server"
        : "Connected";

  return (
    <div className={styles.app}>
      <TopBar
        question={question}
        onQuestionChange={setQuestion}
        onRun={runQuestion}
        onNewQuestion={newQuestion}
        onToggleHistory={() => setHistoryOpen((v) => !v)}
        onShare={run && !blocked ? share : undefined}
        shared={shared}
        running={isRunning}
        status={status}
        hasRun={!!run}
      />

      {(run || isRunning) && <ProvenanceHint />}

      {toast && (
        <div className={styles.toast} role="status">
          {toast}
        </div>
      )}

      <HistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onOpenRun={openRunId}
        onAsk={runQuestion}
      />

      <div className={styles.container}>
        <div className={styles.columns} ref={scrollRef}>
          <main className={styles.notebook}>
            {serverDown && !run && (
              <Banner
                kind="down"
                recorded={recorded}
                onOpenRecorded={openRecorded}
              />
            )}

            {!run && !isRunning ? (
              <StartScreen onRun={runQuestion} />
            ) : blocked ? (
              <BlockedPanel
                reasons={topic?.safety.reasons ?? []}
                onAsk={newQuestion}
              />
            ) : (
              <div className={styles.stages}>
                <StageStrip run={run} isRunning={isRunning} />
                <TryAnother topic={topic} onPick={pivot} />
                {topic && (
                  <RevealStage order={0}>
                    <TopicSection topic={topic} />
                    <NeighborList topic={topic} onExplore={pivot} />
                  </RevealStage>
                )}
                {activeDesignVal && (
                  <RevealStage order={1}>
                    <DesignSection design={activeDesignVal} pair={run?.pair} />
                  </RevealStage>
                )}
                {activeDesignVal && (
                  <RevealStage order={1}>
                    <ReviewThread design={activeDesignVal} />
                  </RevealStage>
                )}
                {sim && (
                  <RevealStage order={2}>
                    <RobotSection sim={sim} />
                  </RevealStage>
                )}
                {report && (
                  <RevealStage order={3}>
                    <UncertaintySection report={report} />
                  </RevealStage>
                )}
                {report && activeDesignVal && (
                  <RevealStage order={3}>
                    <FeedbackCard
                      design={activeDesignVal}
                      report={report}
                      onApply={applyFeedback}
                    />
                  </RevealStage>
                )}
              </div>
            )}

            {!!error && !run && (
              <p className={styles.error}>
                Couldn't run: {errorMessage(error)}
              </p>
            )}
          </main>

          <aside className={styles.bench}>
            {sim && !blocked ? (
              <Deck sim={sim} design={activeDesignVal ?? design} />
            ) : (
              <DeckPlaceholder />
            )}
            {!blocked && active && <LabControls />}
          </aside>
        </div>
      </div>
    </div>
  );
}

function BlockedPanel({
  reasons,
  onAsk,
}: {
  reasons: string[];
  onAsk: () => void;
}) {
  return (
    <div className={styles.blocked}>
      <h2>Lab Planner doesn't design experiments for this topic.</h2>
      <ul>
        {reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
      <p>It designs in-vitro dose-response experiments for benign targets.</p>
      <button className={styles.askDifferent} onClick={onAsk}>
        Ask a different question
      </button>
    </div>
  );
}

function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
