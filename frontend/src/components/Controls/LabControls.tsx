import * as Slider from "@radix-ui/react-slider";
import { useWhatIf } from "../../hooks/useWhatIf";
import { Num } from "../Num/Num";
import { simulated } from "../Num/provenance";
import { fold, nM, uL } from "../../lib/format";
import { plannedLayout } from "../../lib/plate";
import type { ExperimentDesign, UncertaintyReport } from "../../api/types";
import styles from "./LabControls.module.css";

interface Props {
  design: ExperimentDesign;
  report: UncertaintyReport;
}

/** Lab controls / what-if (BRIEF 5.12). Geometry updates live; the server p90 updates on
 *  release, with the old value ghosted. */
export function LabControls({ design, report }: Props) {
  const wi = useWhatIf(design, report);
  const d = wi.draft;
  const used = plannedLayout(d).wellsUsed;
  const prov = () => simulated(wi.report.seed, wi.report.runs);

  const set = (key: keyof typeof wi.patch) => (v: number) =>
    wi.setPatch({ ...wi.patch, [key]: v });

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>Lab controls</h3>

      <Row label="Top concentration" value={nM(d.dilution.top_nM)}>
        <Ctl min={0} max={5} step={0.05}
             value={Math.log10(d.dilution.top_nM)}
             onChange={(v) => set("top_nM")(Math.pow(10, v))}
             onCommit={wi.commit} ariaLabel="Top concentration" />
      </Row>
      <Row label="Dilution factor" value={String(d.dilution.factor)}>
        <Ctl min={2} max={10} step={0.5} value={d.dilution.factor}
             onChange={set("factor")} onCommit={wi.commit} ariaLabel="Dilution factor" />
      </Row>
      <Row label="Concentrations" value={String(d.dilution.points)}>
        <Ctl min={4} max={11} step={1} value={d.dilution.points}
             onChange={set("points")} onCommit={wi.commit} ariaLabel="Concentrations" />
      </Row>
      <Row label="Replicates" value={String(d.replicates)}>
        <Ctl min={1} max={8} step={1} value={d.replicates}
             onChange={set("replicates")} onCommit={wi.commit} ariaLabel="Replicates" />
      </Row>
      <Row label="Transfer volume" value={uL(d.volumes_uL.transfer)}>
        <Ctl min={5} max={100} step={1} value={d.volumes_uL.transfer}
             onChange={set("transfer")} onCommit={wi.commit} ariaLabel="Transfer volume" />
      </Row>

      {wi.notes.length > 0 && (
        <ul className={styles.notes}>{wi.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      )}

      <div className={`${styles.readout} ${wi.pending ? styles.dim : ""}`}>
        <span>p90 <Num value={fold(wi.report.fold_error.p90)} provenance={prov()} /></span>
        <span>median <Num value={fold(wi.report.fold_error.median)} provenance={prov()} /></span>
        <span>wells {used}</span>
        {wi.pending && <span className={styles.pending}>updating…</span>}
      </div>
      <button className={styles.reset} onClick={() => { wi.setPatch({}); }}>
        Reset to designed values
      </button>
    </div>
  );
}

function Row({ label, value, children }: { label: string; value: string; children: React.ReactNode }) {
  return (
    <div className={styles.row}>
      <div className={styles.rowHead}><span>{label}</span><span className={styles.val}>{value}</span></div>
      {children}
    </div>
  );
}

function Ctl({ min, max, step, value, onChange, onCommit, ariaLabel }: {
  min: number; max: number; step: number; value: number;
  onChange: (v: number) => void; onCommit: () => void; ariaLabel: string;
}) {
  return (
    <Slider.Root className={styles.slider} min={min} max={max} step={step}
                 value={[value]}
                 onValueChange={([v]) => onChange(v)}
                 onValueCommit={onCommit}
                 aria-label={ariaLabel}>
      <Slider.Track className={styles.track}><Slider.Range className={styles.range} /></Slider.Track>
      <Slider.Thumb className={styles.thumb} />
    </Slider.Root>
  );
}
