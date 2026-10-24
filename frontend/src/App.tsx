import { useEffect, useState } from "react";
import { APP_NAME } from "./constants";
import { StartScreen } from "./components/Shell/StartScreen";
import { Banner } from "./components/Shell/Banner";
import { DeckPlaceholder } from "./components/Bench/DeckPlaceholder";
import { TopicSection } from "./components/Topic/TopicSection";
import { useRun } from "./hooks/useRun";
import { useHealth } from "./api/queries";
import { loadRecordedIndex, type RecordedIndexEntry } from "./api/recorded";
import { gateOk } from "./api/normalize";
import styles from "./App.module.css";

export function App() {
  const { run, origin, start, openRecorded, isRunning, error } = useRun();
  const health = useHealth();
  const [recorded, setRecorded] = useState<RecordedIndexEntry[]>([]);

  useEffect(() => { loadRecordedIndex().then(setRecorded); }, []);

  const serverDown = health.isError;
  const topic = run?.topic ?? null;
  const blocked = run?.blocked || (topic != null && !gateOk(topic.safety));

  return (
    <div className={styles.app}>
      <header className={styles.topbar}>
        <span className={styles.productName}>{APP_NAME}</span>
        <span className={styles.status}>
          {origin === "recorded" ? "Recorded run" : serverDown ? "Can't reach server" : "Connected"}
        </span>
      </header>

      <div className={styles.columns}>
        <main className={styles.notebook}>
          {serverDown && !run && (
            <Banner kind="down" recorded={recorded} onOpenRecorded={openRecorded} />
          )}

          {!run ? (
            <StartScreen onRun={start} />
          ) : blocked ? (
            <BlockedPanel reasons={topic?.safety.reasons ?? []} />
          ) : (
            <div className={styles.stages}>
              {isRunning && <p className={styles.running}>Running all four stages. Usually a few seconds, longer on the first run of the day.</p>}
              {topic && <TopicSection topic={topic} />}
              {/* stages 2-4 render here as later P0 tasks land */}
            </div>
          )}

          {error && !run && (
            <p className={styles.error}>Couldn't run: {String((error as Error).message)}</p>
          )}
        </main>

        <aside className={styles.bench}>
          <DeckPlaceholder />
        </aside>
      </div>
    </div>
  );
}

function BlockedPanel({ reasons }: { reasons: string[] }) {
  return (
    <div className={styles.blocked}>
      <h2>Lab Planner doesn't design experiments for this topic.</h2>
      <ul>{reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
      <p>It designs in-vitro dose-response experiments for benign targets.</p>
    </div>
  );
}
