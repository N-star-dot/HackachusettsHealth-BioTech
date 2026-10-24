import { useState } from "react";
import styles from "./ProvenanceHint.module.css";

const KEY = "labplanner.provenanceHintDismissed";

function wasDismissed(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}
function remember(): void {
  try { localStorage.setItem(KEY, "1"); } catch { /* storage disabled — best effort */ }
}

/** One-line hint under the top bar on the first run (W1.7): tells the user the numbers are
 *  clickable. Dismissible, remembered in localStorage inside try/catch. */
export function ProvenanceHint() {
  const [hidden, setHidden] = useState(wasDismissed);
  if (hidden) return null;
  const dismiss = () => { remember(); setHidden(true); };
  return (
    <div className={styles.hint} role="note">
      <span>Click any underlined number to see where it came from.</span>
      <button className={styles.close} onClick={dismiss} aria-label="Dismiss hint">Got it</button>
    </div>
  );
}
