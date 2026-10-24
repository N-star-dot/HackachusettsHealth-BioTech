import { EXAMPLES } from "../../constants";
import { loadHistory } from "../../lib/history";
import { realNeighbors } from "../../api/normalize";
import type { TopicReport } from "../../api/types";
import styles from "./TryAnother.module.css";

interface Props {
  topic: TopicReport | null;
  onPick: (q: string) => void;
}

/** One-click "Try another topic" chips (W1.1): examples, nearby topics, recent history. */
export function TryAnother({ topic, onPick }: Props) {
  const neighbors = topic ? realNeighbors(topic).slice(0, 3) : [];
  const history = loadHistory().slice(0, 5);
  const seen = new Set<string>();

  const chips: { label: string; q: string; kind: string }[] = [];
  for (const ex of EXAMPLES) if (!seen.has(ex)) { chips.push({ label: ex, q: ex, kind: "example" }); seen.add(ex); }
  for (const n of neighbors) if (!seen.has(n.name)) { chips.push({ label: n.name, q: n.name, kind: "nearby" }); seen.add(n.name); }
  for (const h of history) if (!seen.has(h.question)) { chips.push({ label: h.question, q: h.question, kind: "recent" }); seen.add(h.question); }

  if (chips.length === 0) return null;

  return (
    <div className={styles.wrap}>
      <span className={styles.label}>Try another topic</span>
      <div className={styles.chips}>
        {chips.map((c) => (
          <button key={c.q} className={`${styles.chip} ${styles[c.kind] ?? ""}`} onClick={() => onPick(c.q)}>
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
