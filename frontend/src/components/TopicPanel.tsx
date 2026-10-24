import { fmt } from "../format";
import type { Source, TopicReport } from "../types";
import { Sourced } from "./Sourced";

export function TopicPanel({ topic }: { topic: TopicReport }) {
  const topicSource: Source = { type: "openalex", id: topic.topic.openalex_id };
  const maxWorks = Math.max(1, ...topic.counts_by_year.map((c) => c.works));

  return (
    <div className="card card--side">
      <div>
        <p className="eyebrow">OpenAlex topic</p>
        <h3>{topic.topic.name}</h3>
        <span className="mono muted small">{topic.topic.openalex_id}</span>
      </div>

      <div className="stat-line">
        <Sourced source={topicSource} note={`Momentum model ${topic.momentum.model}`} className="mono stat-line__value">
          {fmt.num(topic.momentum.p_growth)}
        </Sourced>
        <span className="muted small">probability the topic grows faster than typical</span>
      </div>

      <div className="years">
        <span className="label">Works per year</span>
        <div className="years__chart">
          {topic.counts_by_year.map((c) => (
            <div className="years__col" key={c.year}>
              <Sourced source={c.source} className="mono small">
                {fmt.int(c.works)}
              </Sourced>
              <span className="years__bar" style={{ height: `${(c.works / maxWorks) * 82}px` }} aria-hidden="true" />
              <span className="mono muted small">{c.year}</span>
            </div>
          ))}
        </div>
      </div>

      {topic.neighbors.length > 0 && (
        <div className="neighbors">
          <span className="label">Neighbor topics</span>
          {topic.neighbors.map((n) => {
            const src: Source = { type: "openalex", id: n.openalex_id };
            return (
              <div className="neighbor" key={n.openalex_id}>
                <span>{n.name}</span>
                <span className="mono muted small">
                  <Sourced source={src}>{fmt.int(n.works_last_5y)}</Sourced> works (5 y)
                  {n.p_growth != null && (
                    <>
                      {" · "}
                      <Sourced source={src} note={`Momentum model ${topic.momentum.model}`}>
                        {fmt.num(n.p_growth)}
                      </Sourced>
                    </>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
