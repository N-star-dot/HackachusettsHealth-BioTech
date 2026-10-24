import { useState } from "react";
import { APP_NAME } from "./constants";
import { StartScreen } from "./components/Shell/StartScreen";
import { DeckPlaceholder } from "./components/Bench/DeckPlaceholder";
import styles from "./App.module.css";

export function App() {
  // P0-1: shell + start screen only. The run flow + workspace land in P0-2 onward.
  const [started, setStarted] = useState(false);

  return (
    <div className={styles.app}>
      <header className={styles.topbar}>
        <span className={styles.productName}>{APP_NAME}</span>
        <span className={styles.status}>History</span>
      </header>

      <div className={styles.columns}>
        <main className={styles.notebook}>
          {!started ? (
            <StartScreen onRun={() => setStarted(true)} />
          ) : (
            <p>Run flow arrives in the next task.</p>
          )}
        </main>
        <aside className={styles.bench}>
          <DeckPlaceholder />
        </aside>
      </div>
    </div>
  );
}
