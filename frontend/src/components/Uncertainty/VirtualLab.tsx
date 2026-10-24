import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { scaleLog } from "d3-scale";
import { Num } from "../Num/Num";
import { simulated } from "../Num/provenance";
import { fold } from "../../lib/format";
import type { UncertaintyReport } from "../../api/types";
import styles from "./VirtualLab.module.css";

interface Props {
  report: UncertaintyReport;
  baseline?: UncertaintyReport | null; // ghost outline when a draft differs from the run
}

type Band = "ok" | "partial" | "flag";
export function bandOf(fe: number): Band {
  if (fe <= 1.5) return "ok";
  if (fe <= 2) return "partial";
  return "flag";
}
const BAND_COLOR: Record<Band, string> = {
  ok: "var(--ok)",
  partial: "var(--partial-mark)",
  flag: "var(--flag)",
};

/** The virtual lab (V2): makes the Monte Carlo visible. A true-vs-measured scatter on
 *  log-log axes with the identity line and 1.5x/2x bands, dots colored by fold error and
 *  hollow when the true IC50 fell outside the tested range, plus a fold-error histogram
 *  with median and p90 markers. Dots land over ~1.5 s (reduced motion: all at once). */
export function VirtualLab({ report, baseline }: Props) {
  const s = report.samples;
  const reduced = useReducedMotion() ?? false;
  const n = s?.true_ic50_nM.length ?? 0;

  // count-up as dots land
  const [shown, setShown] = useState(reduced ? n : 0);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    if (reduced || n === 0) { setShown(n); return; }
    setShown(0);
    const start = performance.now();
    const dur = 1500;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      setShown(Math.round(p * n));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [n, reduced, report.design_id]);

  if (!s || n === 0) return null;

  const prov = () => simulated(report.seed, report.runs);

  // tested range from the dose-response curve (the dilution concentrations)
  const concs = report.curve?.concentrations_nM ?? [];
  const lo = concs.length ? Math.min(...concs) : -Infinity;
  const hi = concs.length ? Math.max(...concs) : Infinity;

  return (
    <div className={styles.lab}>
      <div className={styles.head}>
        <h3 className={styles.title}>{report.runs.toLocaleString()} virtual experiments</h3>
        <span className={styles.count}>{shown.toLocaleString()} shown</span>
      </div>

      <Scatter s={s} lo={lo} hi={hi} shown={shown} />
      <Histogram report={report} baseline={baseline} />

      <p className={styles.label}>
        Simulated, seed {report.seed}, {report.runs.toLocaleString()} runs. Showing{" "}
        {n.toLocaleString()} of them. p90{" "}
        <Num value={fold(report.fold_error.p90)} provenance={prov()} />, median{" "}
        <Num value={fold(report.fold_error.median)} provenance={prov()} />.
      </p>
    </div>
  );
}

function Scatter({ s, lo, hi, shown }: {
  s: NonNullable<UncertaintyReport["samples"]>; lo: number; hi: number; shown: number;
}) {
  const w = 560, h = 360, pad = 44;
  const all = [...s.true_ic50_nM, ...s.recovered_ic50_nM].filter((v) => v > 0);
  const min = Math.min(...all), max = Math.max(...all);
  const x = scaleLog().domain([min, max]).range([pad, w - pad]).clamp(true);
  const y = scaleLog().domain([min, max]).range([h - pad, pad]).clamp(true);

  // diagonal identity + fold bands (measured = true * k)
  const diag = (k: number) => {
    const x1 = x(min), y1 = y(min * k);
    const x2 = x(max), y2 = y(max * k);
    return { x1, y1, x2, y2 };
  };
  const id = diag(1), up15 = diag(1.5), dn15 = diag(1 / 1.5), up2 = diag(2), dn2 = diag(1 / 2);

  const ticks = logTicks(min, max);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={styles.scatter} role="img"
         aria-label="True versus measured IC50 for each simulated experiment, log-log">
      {/* axes */}
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
      <line x1={pad} y1={pad} x2={pad} y2={h - pad} stroke="var(--rule)" />
      {ticks.map((t) => (
        <g key={`x${t}`}>
          <line x1={x(t)} y1={h - pad} x2={x(t)} y2={h - pad + 4} stroke="var(--graphite)" />
          <text x={x(t)} y={h - pad + 14} className={styles.tick} textAnchor="middle">{fmtNM(t)}</text>
        </g>
      ))}
      {ticks.map((t) => (
        <g key={`y${t}`}>
          <line x1={pad - 4} y1={y(t)} x2={pad} y2={y(t)} stroke="var(--graphite)" />
          <text x={pad - 6} y={y(t) + 3} className={styles.tick} textAnchor="end">{fmtNM(t)}</text>
        </g>
      ))}
      <text x={(w) / 2} y={h - 6} className={styles.axisLabel} textAnchor="middle">True IC50 (nM)</text>
      <text transform={`translate(12 ${h / 2}) rotate(-90)`} className={styles.axisLabel} textAnchor="middle">Measured IC50 (nM)</text>

      {/* fold bands */}
      <line {...up2} stroke="var(--rule)" strokeDasharray="4 3" />
      <line {...dn2} stroke="var(--rule)" strokeDasharray="4 3" />
      <line {...up15} stroke="var(--rule)" strokeDasharray="2 3" />
      <line {...dn15} stroke="var(--rule)" strokeDasharray="2 3" />
      <line {...id} stroke="var(--ink)" strokeWidth={1} />

      {/* dots */}
      {s.true_ic50_nM.map((tv, i) => {
        if (i >= shown) return null;
        const mv = s.recovered_ic50_nM[i];
        if (!(tv > 0) || !(mv > 0)) return null;
        const band = bandOf(s.fold_error[i] ?? 1);
        const outside = tv < lo || tv > hi;
        return (
          <circle key={i} cx={x(tv)} cy={y(mv)} r={2.4}
                  fill={outside ? "none" : BAND_COLOR[band]}
                  stroke={BAND_COLOR[band]} strokeWidth={outside ? 1 : 0}
                  opacity={0.72}>
            <title>true {fmtNM(tv)} nM, measured {fmtNM(mv)} nM, {(s.fold_error[i] ?? 1).toFixed(2)}x</title>
          </circle>
        );
      })}
    </svg>
  );
}

function Histogram({ report, baseline }: { report: UncertaintyReport; baseline?: UncertaintyReport | null }) {
  const fe = report.samples?.fold_error ?? [];
  if (fe.length === 0) return null;
  const w = 560, h = 130, pad = 36;
  const max = Math.max(...fe, report.fold_error.p90, 2);
  const bins = 28;
  const x = scaleLog().domain([1, max]).range([pad, w - pad]).clamp(true);
  const edges = Array.from({ length: bins + 1 }, (_, i) => Math.pow(max, i / bins));
  const counts = histogram(fe, edges);
  const ghostCounts = baseline?.samples?.fold_error
    ? histogram(baseline.samples.fold_error, edges)
    : null;
  const peak = Math.max(1, ...counts, ...(ghostCounts ?? []));
  const barH = (c: number) => (c / peak) * (h - pad * 2);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={styles.hist} role="img"
         aria-label="Fold-error histogram with median and p90 markers">
      <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--rule)" />
      {ghostCounts && ghostCounts.map((c, i) => (
        <rect key={`g${i}`} x={x(edges[i])} y={h - pad - barH(c)}
              width={Math.max(1, x(edges[i + 1]) - x(edges[i]) - 1)} height={barH(c)}
              fill="none" stroke="var(--graphite)" strokeWidth={0.6} opacity={0.5} />
      ))}
      {counts.map((c, i) => (
        <rect key={i} x={x(edges[i])} y={h - pad - barH(c)}
              width={Math.max(1, x(edges[i + 1]) - x(edges[i]) - 1)} height={barH(c)}
              fill="var(--inhibited)" opacity={0.6} />
      ))}
      <Marker x={x(report.fold_error.median)} h={h} pad={pad} color="var(--ink)" label={`median ${fold(report.fold_error.median)}`} />
      <Marker x={x(report.fold_error.p90)} h={h} pad={pad} color="var(--active)" label={`p90 ${fold(report.fold_error.p90)}`} />
      {[1.5, 2].map((k) => (
        <line key={k} x1={x(k)} y1={pad} x2={x(k)} y2={h - pad} stroke="var(--rule)" strokeDasharray="2 3" />
      ))}
      <text x={w - pad} y={h - 6} className={styles.axisLabel} textAnchor="end">Fold error (lower is better)</text>
    </svg>
  );
}

function Marker({ x, h, pad, color, label }: { x: number; h: number; pad: number; color: string; label: string }) {
  return (
    <g>
      <line x1={x} y1={pad - 4} x2={x} y2={h - pad} stroke={color} strokeWidth={1.2} />
      <text x={x + 3} y={pad + 4} className={styles.markerLabel} fill={color}>{label}</text>
    </g>
  );
}

export function histogram(values: number[], edges: number[]): number[] {
  const counts = new Array(edges.length - 1).fill(0);
  for (const v of values) {
    const vv = Math.max(1, v);
    for (let i = 0; i < edges.length - 1; i++) {
      if (vv >= edges[i] && (vv < edges[i + 1] || i === edges.length - 2)) { counts[i]++; break; }
    }
  }
  return counts;
}

function logTicks(min: number, max: number): number[] {
  const out: number[] = [];
  const lo = Math.floor(Math.log10(min));
  const hi = Math.ceil(Math.log10(max));
  for (let e = lo; e <= hi; e++) out.push(Math.pow(10, e));
  return out.filter((t) => t >= min / 2 && t <= max * 2);
}

function fmtNM(v: number): string {
  if (v >= 1000) return `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k`;
  if (v >= 1) return `${v.toFixed(v >= 10 ? 0 : 1)}`;
  return v.toPrecision(2);
}
