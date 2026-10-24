import { StatusBadge } from "./StatusBadge";
import { ruleChecks } from "../../lib/ruleChecks";
import { nM } from "../../lib/format";
import { concentrations } from "../../lib/dilution";
import { verifiedCount } from "../../api/normalize";
import { FONT_QUOTE } from "../../design/fonts";
import type { ExperimentDesign, RationaleItem } from "../../api/types";
import styles from "./ReviewThread.module.css";

interface Props {
  design: ExperimentDesign;
}

/** Design review (the debate): a code-rendered designer turn, one citation-checker turn
 *  per rationale item, browser rule checks, and skeptic turns. Model text is NEVER shown
 *  as verified (BRIEF 5.8 / rule R0.3). */
export function ReviewThread({ design }: Props) {
  const { verified, total } = verifiedCount(design);
  const unverified = design.rationale.filter((r) => r.status !== "verified");
  const checks = ruleChecks(design);
  const concs = concentrations(design.dilution.top_nM, design.dilution.factor, design.dilution.points);

  return (
    <section className={styles.section}>
      <h3 className={styles.title}>Design review</h3>
      <p className={styles.summary}>{verified} of {total} evidence items verified</p>
      {unverified.length > 0 && (
        <p className={styles.alert}>{unverified.length} items could not be verified</p>
      )}

      {/* designer turn — rendered from the design, never from model text */}
      <div className={styles.turn}>
        <div className={styles.role}>Designer</div>
        <p>
          Proposed {design.dilution.points} concentrations at a {design.dilution.factor}-fold
          dilution from {nM(concs[0])} to {nM(concs[concs.length - 1])}, {design.replicates}{" "}
          replicates, {design.controls.positive_wells} positive and {design.controls.negative_wells}{" "}
          negative controls, starting from the median of {design.prior_ic50.n_measurements} ChEMBL
          measurements.
        </p>
      </div>

      {design.rationale.map((item, i) => (
        <CitationTurn key={i} item={item} />
      ))}

      {/* rule checks */}
      <div className={styles.turn}>
        <div className={styles.role}>Rule checks</div>
        <ul className={styles.rules}>
          {checks.map((c, i) => (
            <li key={i} className={c.pass ? styles.pass : styles.fail}>
              <span aria-hidden>{c.pass ? "✓" : "✗"}</span> {c.label}
            </li>
          ))}
        </ul>
      </div>

      {/* skeptic turns (B2.5) when present */}
      {design.review?.map((turn, i) => (
        <div key={`sk${i}`} className={styles.turn}>
          <div className={styles.role}>Skeptic</div>
          <p className={styles.modelNote} style={{ fontFamily: FONT_QUOTE }}>
            {turn.argument}
          </p>
          <p className={styles.modelLabel}>Model's argument, not verified</p>
          <p className={styles.verdict}>
            Proposed {turn.field} = {turn.proposed_value}. p90 {turn.p90_before.toFixed(2)}x to{" "}
            {turn.p90_after.toFixed(2)}x, +{turn.extra_tips} tips.{" "}
            {turn.verdict === "supported"
              ? "Simulation supports this change."
              : "Simulation doesn't support this change."}
          </p>
        </div>
      ))}
    </section>
  );
}

function CitationTurn({ item }: { item: RationaleItem }) {
  const isQuote = item.evidence_type === "abstract_quote";
  return (
    <div className={styles.turn}>
      <div className={styles.role}>Citation checker</div>
      {isQuote ? (
        <>
          {item.quote && (
            <blockquote className={styles.quote} style={{ fontFamily: FONT_QUOTE }}>
              "{item.quote}"
            </blockquote>
          )}
          {item.pmid && (
            <a className={styles.pmid} href={`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/`}
               target="_blank" rel="noreferrer">PMID {item.pmid}</a>
          )}
          {item.model_note && (
            <>
              <p className={styles.modelNote}>{item.model_note}</p>
              <p className={styles.modelLabel}>Model's note, not verified</p>
            </>
          )}
        </>
      ) : (
        <>
          <p className={styles.claim}>{item.claim}</p>
          {item.url && (
            <a className={styles.pmid} href={item.url} target="_blank" rel="noreferrer">
              {item.document_chembl_id ? `Source paper ${item.document_chembl_id}` : `ChEMBL activity ${item.evidence_id}`}
            </a>
          )}
        </>
      )}
      <StatusBadge
        status={item.status}
        label={item.status === "verified" ? (isQuote ? "Verified quote" : "Verified record") : undefined}
      />
      {item.status !== "verified" && item.reason && (
        <p className={styles.reason}>{item.reason}</p>
      )}
    </div>
  );
}
