import { Num } from "../Num/Num";
import { src } from "../Num/provenance";
import type { TopicReport } from "../../api/types";
import styles from "./CountsChart.module.css";

interface Props {
  topic: TopicReport;
}

/** Yearly publication counts as hand-built SVG bars (BRIEF 5.4). Last 5 years (the
 *  crowding window) in ink; earlier in graphite. Hidden table for screen readers. */
export function CountsChart({ topic }: Props) {
  const counts = topic.counts_by_year;
  if (counts.length === 0) return null;

  const w = 320;
  const h = 120;
  const pad = 24;
  const max = Math.max(...counts.map((c) => c.works), 1);
  const bw = (w - pad * 2) / counts.length;
  const lastFiveCut = Math.max(...counts.map((c) => c.year)) - 4;

  return (
    <div className={styles.wrap}>
      <svg viewBox={`0 0 ${w} ${h}`} className={styles.svg} role="img"
           aria-label={`Yearly works for ${topic.topic.name}, ${counts[0].year} to ${counts[counts.length - 1].year}`}>
        {/* baseline */}
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" strokeWidth="1" />
        {counts.map((c, i) => {
          const bh = ((c.works / max) * (h - pad * 2));
          const x = pad + i * bw;
          const y = h - pad - bh;
          const recent = c.year >= lastFiveCut;
          return (
            <rect key={c.year} x={x + 1} y={y} width={bw - 2} height={bh}
                  fill={recent ? "var(--ink)" : "var(--graphite)"}>
              <title>{c.year}: {c.works} works</title>
            </rect>
          );
        })}
      </svg>
      <div className={styles.axisLabel}>Works per year</div>
      <div className={styles.hint}>
        Last year:{" "}
        <Num value={`${counts[counts.length - 1].works} works`}
             provenance={src(counts[counts.length - 1].source,
               `OpenAlex topic ${topic.topic.openalex_id}, works grouped by publication year`)} />
      </div>

      {/* visually hidden data table */}
      <table className={styles.srOnly}>
        <caption>Yearly works</caption>
        <tbody>
          {counts.map((c) => (
            <tr key={c.year}><th>{c.year}</th><td>{c.works}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
