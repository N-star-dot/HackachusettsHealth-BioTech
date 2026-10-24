import { CountsChart } from "./CountsChart";
import { MomentumScale } from "./MomentumScale";
import { MatrixTable } from "../Matrix/MatrixTable";
import { sourceUrl } from "../../lib/provenance";
import { isOfflineTopic } from "../../api/normalize";
import type { TopicReport } from "../../api/types";
import styles from "./TopicSection.module.css";

interface Props {
  topic: TopicReport;
}

export function TopicSection({ topic }: Props) {
  const offline = isOfflineTopic(topic);
  const topicUrl = sourceUrl({ type: "openalex", id: topic.topic.openalex_id });

  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <span className={styles.numeral}>1</span>
        <h2 className={styles.name}>
          {topic.topic.name}
          {topicUrl && (
            <a className={styles.sourceLink} href={topicUrl} target="_blank" rel="noreferrer">
              Topic in OpenAlex
            </a>
          )}
        </h2>
      </div>

      {offline ? (
        <p className={styles.offline}>
          OpenAlex couldn't be reached, so topic numbers aren't shown. The experiment below
          doesn't depend on them.
        </p>
      ) : (
        <>
          <CountsChart topic={topic} />
          <MomentumScale topic={topic} />
        </>
      )}

      <MatrixTable topic={topic} />
    </section>
  );
}
