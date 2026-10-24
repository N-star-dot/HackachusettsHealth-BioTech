import * as Slider from "@radix-ui/react-slider";
import { useWhatIf } from "../../hooks/useWhatIf";
import { useUIStore } from "../../state/store";
import { Num } from "../Num/Num";
import { simulated } from "../Num/provenance";
import { CompareChart } from "./CompareChart";
import { fold, nM, uL } from "../../lib/format";
import { plannedLayout } from "../../lib/plate";
import type { ExperimentDesign, NextExperiment, UncertaintyReport } from "../../api/types";
import styles from "./LabControls.module.css";

interface Props {
  design: ExperimentDesign;
  report: UncertaintyReport;
}

/** Lab controls / what-if (BRIEF 5.12). Geometry updates live; the server p90 updates on
 *  release, with the old value ghosted. */
export function LabControls({ design, report }: Props) {
  const wi = useWhatIf(design, report);
  const addPin = useUIStore((s) => s.addPin);
  const pins = useUIStore((s) => s.pins);
  const d = wi.draft;
  const used = plannedLayout(d).wellsUsed;
  const prov = () => simulated(wi.report.seed, wi.report.runs);

  const set = (key: keyof typeof wi.patch) => (v: number) =>
    wi.setPatch({ ...wi.patch, [key]: v });

  // "Try this change": apply a suggestion's design deltas as a what-if patch
  const tryChange = (ne: NextExperiment) => {
    if (!ne.design) return;
    wi.setPatch({
      top_nM: ne.design.dilution.top_nM,
      factor: ne.design.dilution.factor,
      points: ne.design.dilution.points,
      replicates: ne.design.replicates,
      transfer: ne.design.volumes_uL.transfer,
    });
    wi.commit();
  };

  const estTips = plannedLayout(d).wellsUsed; // proxy cost for the chart x-axis

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

      {wi.report.next_experiments.length > 0 && (
        <div className={styles.suggestions}>
          {wi.report.next_experiments.map((ne, i) => (
            <button key={i} className={styles.try} disabled={!ne.design} onClick={() => tryChange(ne)}>
              Try: {ne.change}
            </button>
          ))}
        </div>
      )}

      <div className={styles.pinRow}>
        <button className={styles.pin}
          onClick={() => addPin(design.assay.compound_chembl_id, estTips, wi.report.fold_error.p90)}
          disabled={pins.length >= 4}>
          Pin for comparison
        </button>
        {pins.map((p) => <span key={p.letter} className={styles.chip}>{p.letter}</span>)}
      </div>

      <CompareChart currentTips={estTips} currentP90={wi.report.fold_error.p90}
                    suggestions={wi.report.next_experiments} />
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
