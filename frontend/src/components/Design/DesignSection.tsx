import { Num } from "../Num/Num";
import { src } from "../Num/provenance";
import { DilutionLadder } from "./DilutionLadder";
import { PlateMap } from "./PlateMap";
import { plannedLayout } from "../../lib/plate";
import { labwareName, chemblName } from "../../lib/labware";
import { nM } from "../../lib/format";
import { sourceUrl } from "../../lib/provenance";
import type { ExperimentDesign, PairInfo } from "../../api/types";
import styles from "./DesignSection.module.css";

interface Props {
  design: ExperimentDesign;
  pair?: PairInfo | null;
}

export function DesignSection({ design, pair }: Props) {
  const compound = pair?.compound_name ?? chemblName(design.assay.compound_chembl_id);
  const target = pair?.target_name ?? chemblName(design.assay.target_chembl_id);
  const prior = design.prior_ic50;
  const foldSpread = Math.pow(10, prior.spread_log10);
  const used = plannedLayout(design).wellsUsed;

  const compoundUrl = sourceUrl({ type: "chembl_activity", id: design.assay.compound_chembl_id });
  const targetUrl = sourceUrl({ type: "chembl_activity", id: design.assay.target_chembl_id });

  return (
    <section className={styles.section}>
      <div className={styles.head}>
        <span className={styles.numeral}>2</span>
        <h2 className={styles.name}>
          {cap(compound)} on {target}
          <span className={styles.ids}>
            {compoundUrl && <a href={compoundUrl} target="_blank" rel="noreferrer">{design.assay.compound_chembl_id}</a>}
            {targetUrl && <a href={targetUrl} target="_blank" rel="noreferrer">{design.assay.target_chembl_id}</a>}
          </span>
        </h2>
      </div>

      {pair?.match === "default" && (
        <p className={styles.notice}>
          Your question didn't match a prepared compound and target, so this design uses
          lapatinib on HER2 as a worked example.
        </p>
      )}

      <p className={styles.ic50}>
        IC50 is the concentration that cuts the target's activity in half. Lower means more potent.
      </p>

      <p className={styles.guess}>
        Starting guess:{" "}
        <Num value={nM(prior.median_nM)} provenance={src(prior.source,
          `Median of ${prior.n_measurements} published measurements in ChEMBL.`)} />
        , the median of {prior.n_measurements} published measurements in ChEMBL. Labs disagree
        by about {foldSpread.toFixed(1)}-fold (one standard deviation).
      </p>

      <DilutionLadder design={design} />
      <PlateMap design={design} />

      <ul className={styles.facts}>
        <li>Replicates: {design.replicates}</li>
        <li>Controls: {design.controls.positive_wells} positive, {design.controls.negative_wells} negative</li>
        <li>Wells used: {used} of 96</li>
        <li>Transfer {design.volumes_uL.transfer} µL, diluent {design.volumes_uL.diluent} µL</li>
        <li>Pipette: {labwareName(design.pipette)}</li>
        <li>Tip rack: {labwareName(design.tiprack)}</li>
        <li>Plate: {labwareName(design.plate.labware)}</li>
      </ul>

      {design.notes && design.notes.length > 0 && (
        <ul className={styles.notes}>{design.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      )}
    </section>
  );
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
