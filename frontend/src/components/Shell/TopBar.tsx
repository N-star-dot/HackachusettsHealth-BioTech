import { useEffect, useState } from "react";
import { APP_NAME } from "../../constants";
import styles from "./TopBar.module.css";

interface Props {
  question: string;
  onQuestionChange: (q: string) => void;
  onRun: (q: string) => void;
  onNewQuestion: () => void;
  onToggleHistory: () => void;
  onShare?: () => void;
  shared?: boolean;
  running: boolean;
  status: string;
  hasRun: boolean;
}

/** Persistent top bar (W1.1): the question field stays after a run so you can try another
 *  topic without reloading. */
export function TopBar({
  question, onQuestionChange, onRun, onNewQuestion, onToggleHistory,
  onShare, shared, running, status, hasRun,
}: Props) {
  const [draft, setDraft] = useState(question);
  useEffect(() => setDraft(question), [question]);

  const submit = () => {
    const q = draft.trim();
    if (q && !running) { onQuestionChange(q); onRun(q); }
  };

  return (
    <header className={styles.topbar}>
      <span className={styles.productName}>{APP_NAME}</span>
      <div className={styles.field}>
        <input
          className={styles.input}
          value={draft}
          placeholder="What do you want to test?"
          aria-label="Research question"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
        />
        <button className={styles.run} onClick={submit} disabled={!draft.trim() || running}>
          {running ? "Running" : "Run"}
        </button>
      </div>
      <div className={styles.actions}>
        {hasRun && <button className={styles.text} onClick={onNewQuestion}>New question</button>}
        <button className={styles.text} onClick={onToggleHistory}>History</button>
        {hasRun && onShare && (
          <button className={styles.text} onClick={onShare}>{shared ? "Link copied" : "Share"}</button>
        )}
        <span className={styles.status}>{status}</span>
      </div>
    </header>
  );
}
