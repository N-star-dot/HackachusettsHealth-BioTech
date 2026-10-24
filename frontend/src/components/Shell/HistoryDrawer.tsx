import { useEffect } from "react";
import { loadHistory } from "../../lib/history";
import styles from "./HistoryDrawer.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
  onOpenRun: (runId: string) => void;
  onAsk: (question: string) => void;
}

/** Slide-in list of past runs (W1.1). Re-open a saved run by id, or re-ask its question. */
export function HistoryDrawer({ open, onClose, onOpenRun, onAsk }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  const entries = loadHistory();

  return (
    <div className={styles.scrim} onClick={onClose}>
      <aside className={styles.drawer} onClick={(e) => e.stopPropagation()} aria-label="Run history">
        <div className={styles.head}>
          <h2 className={styles.title}>Recent runs</h2>
          <button className={styles.close} onClick={onClose} aria-label="Close history">Close</button>
        </div>
        {entries.length === 0 ? (
          <p className={styles.empty}>No runs yet. Your past questions will show up here.</p>
        ) : (
          <ul className={styles.list}>
            {entries.map((e) => (
              <li key={e.runId} className={styles.item}>
                <button className={styles.question} onClick={() => { onOpenRun(e.runId); onClose(); }}>
                  {e.question}
                </button>
                <p className={styles.meta}>{e.topicName}</p>
                <button className={styles.reask} onClick={() => { onAsk(e.question); onClose(); }}>
                  Ask again
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>
    </div>
  );
}
