import { Num } from "../Num/Num";
import { simulated, src, assumed } from "../Num/provenance";
import { fold, pct } from "../../lib/format";
import type { Source, UncertaintyReport } from "../../api/types";
import styles from "./UncertaintySection.module.css";

interface Props {
  report: UncertaintyReport;
}

/** The whole section lives in a 'simulated' block (BRIEF 5.11): only noise levels and
 *  calibration carry real sources; the readouts are synthetic. Every number has provenance. */
export function UncertaintySection({ report }: Props) {
  const { fold_error, noise, calibration, runs, seed } = report;
  const sim = () => simulated(seed, runs);
  const fieldSrc = (k: keyof NonNullable<typeof noise.field_sources>): Source | undefined =>
    noise.field_sources?.[k];
  const noiseProv = (k: Parameters<typeof fieldSrc>[0]) => {
    const s = fieldSrc(k);
    return s ? src(s) : assumed("assumed noise level");
  };

  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <span className={styles.numeral}>4</span>
        <h2 className={styles.name}>Uncertainty</h2>
      </div>

      <div className={styles.simBlock}>
        <span className={styles.simLabel}>Simulated, seed {seed}, {runs.toLocaleString()} runs</span>

        <p className={styles.headline}>
          <Num value={fold(fold_error.p90)} className={styles.big} provenance={sim()} />
        </p>
        <p className={styles.sentence}>
          In 9 of 10 simulated experiments, the measured IC50 lands within{" "}
          <Num value={fold(fold_error.p90)} provenance={sim()} /> of the true value. Half land
          within <Num value={fold(fold_error.median)} provenance={sim()} />.
        </p>

        <p className={styles.risk}>
          In <Num value={pct(report.outside_range_share)} provenance={sim()} /> of simulated runs
          the true IC50 fell outside the tested range.{" "}
          <Num value={pct(report.failed_fit_share)} provenance={sim()} /> of curve fits failed.
        </p>

        <table className={styles.noise}>
          <tbody>
            <tr>
              <td>Lab-to-lab spread</td>
              <td><Num value={`${noise.lab_spread_log10} log units (${Math.pow(10, noise.lab_spread_log10).toFixed(1)}-fold)`} provenance={noiseProv("lab_spread_log10")} /></td>
            </tr>
            <tr>
              <td>Pipetting scatter</td>
              <td><Num value={pct(noise.pipette_cv)} provenance={noiseProv("pipette_cv")} /></td>
            </tr>
            <tr>
              <td>Pipetting bias</td>
              <td><Num value={pct(noise.pipette_bias)} provenance={noiseProv("pipette_bias")} /></td>
            </tr>
            <tr>
              <td>Plate reader scatter</td>
              <td><Num value={pct(noise.reader_cv)} provenance={noiseProv("reader_cv")} /></td>
            </tr>
          </tbody>
        </table>
        <p className={styles.note}>Biology dominates. Labs disagree far more than the robot errs.</p>

        <p className={styles.calibration}>
          Checked against real data: the 90% range contained{" "}
          <Num value={pct(calibration.coverage_90)} provenance={assumed("Leave-one-out coverage against real ChEMBL measurement groups.")} />{" "}
          of {calibration.pairs.toLocaleString()} held-out ChEMBL measurements. The target is 90%.
        </p>

        {report.next_experiments.length > 0 && (
          <div className={styles.next}>
            <h3 className={styles.nextTitle}>Best next changes</h3>
            <ul>
              {report.next_experiments.map((ne, i) => (
                <li key={i}>
                  {ne.change} —{" "}
                  <Num
                    value={ne.p90_after != null
                      ? `p90 ${fold(fold_error.p90)} to ${fold(ne.p90_after)}`
                      : `${ne.p90_fold_error_drop_pct}% less excess error`}
                    provenance={sim()} />{" "}
                  (+{ne.extra_tips} tips, +{ne.extra_compound_uL} µL compound)
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
