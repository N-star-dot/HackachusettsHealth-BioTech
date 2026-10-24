import { api } from "../../api/client";
import type { RecordedIndexEntry } from "../../api/recorded";
import styles from "./Banner.module.css";

interface Props {
  kind: "down" | "waking";
  recorded: RecordedIndexEntry[];
  onOpenRecorded: (file: string) => void;
}

/** Server-down / cold-start banner (BRIEF 5.1). Offers recorded runs. */
export function Banner({ kind, recorded, onOpenRecorded }: Props) {
  return (
    <div className={styles.banner} role="status">
      {kind === "down" ? (
        <p>
          Can't reach the Lab Planner server at {api.baseUrl()}. Start it with{" "}
          <code>uvicorn backend.api:app --reload</code>, or open a recorded run.
        </p>
      ) : (
        <p>The server is waking up. Free hosting can take up to a minute.</p>
      )}
      {recorded.length > 0 && (
        <ul className={styles.list}>
          {recorded.map((r) => (
            <li key={r.file}>
              <button className={styles.link} onClick={() => onOpenRecorded(r.file)}>
                Open a recorded run: {r.question}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
