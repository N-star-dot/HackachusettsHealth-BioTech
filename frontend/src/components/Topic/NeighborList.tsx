import { realNeighbors } from "../../api/normalize";
import { prob } from "../../lib/format";
import type { TopicReport } from "../../api/types";
import styles from "./NeighborList.module.css";

interface Props {
  topic: TopicReport;
  onExplore: (name: string) => void;
}

/** Less explored topics nearby (BRIEF 5.5): only shown when real neighbors exist. */
export function NeighborList({ topic, onExplore }: Props) {
  const neighbors = realNeighbors(topic);
  if (neighbors.length === 0) return null;

  const thisWorks = topic.counts_by_year
    .filter((c) => c.year >= 2020)
    .reduce((s, c) => s + c.works, 0);

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Less explored topics nearby</h3>
      <ul className={styles.list}>
        {neighbors.map((n) => (
          <li key={n.openalex_id} className={styles.row}>
            <span className={styles.name}>{n.name}</span>
            <span className={styles.meta}>
              {n.works_last_5y.toLocaleString()} works in 5y
              {n.p_growth != null && `, momentum ${prob(n.p_growth)}`}
              {thisWorks > 0 && `, ${(n.works_last_5y / thisWorks).toFixed(2)}x this topic`}
            </span>
            <button className={styles.explore} onClick={() => onExplore(n.name)}>
              Explore this topic
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
