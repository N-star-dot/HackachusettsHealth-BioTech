import * as Popover from "@radix-ui/react-popover";
import type { Provenance } from "./provenance";
import { KIND_LABEL, sourceUrl } from "../../lib/provenance";
import styles from "./Num.module.css";

interface Props {
  value: string;              // already-formatted text
  provenance: Provenance;
  className?: string;
}

/** Every number on screen renders through <Num> with a source (BRIEF 5.15 / rule R0.1).
 *  A dotted underline opens a provenance popover. In dev, a missing provenance is a bug
 *  (magenta outline + console warning) — caught by a test. */
export function Num({ value, provenance, className }: Props) {
  if (import.meta.env.DEV && !provenance) {
    // eslint-disable-next-line no-console
    console.warn("<Num> rendered without provenance:", value);
  }
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={`${styles.num} num ${className ?? ""}`}
          data-num
          data-provenance={provenance.kind}
        >
          {value}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className={styles.pop} sideOffset={6}>
          <ProvenanceBody p={provenance} />
          <Popover.Arrow className={styles.arrow} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function Link({ href, children }: { href: string | null; children: React.ReactNode }) {
  if (!href) return <span>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

function ProvenanceBody({ p }: { p: Provenance }) {
  if (p.kind === "source") {
    return (
      <div className={styles.body}>
        <div className={styles.kind}>{KIND_LABEL[p.source.type] ?? p.source.type}</div>
        <div className={styles.id}>
          <Link href={sourceUrl(p.source)}>{p.source.id}</Link>
        </div>
        {p.note && <div className={styles.note}>{p.note}</div>}
      </div>
    );
  }
  if (p.kind === "simulated") {
    return (
      <div className={styles.body}>
        <div className={styles.kind}>Simulated (seed {p.seed}, {p.runs} runs)</div>
        {p.sources?.map((s, i) => (
          <div key={i} className={styles.id}>
            <Link href={sourceUrl(s)}>{KIND_LABEL[s.type] ?? s.type}: {s.id}</Link>
          </div>
        ))}
      </div>
    );
  }
  if (p.kind === "assumed") {
    return (
      <div className={styles.body}>
        <div className={styles.kind}>Assumed value</div>
        <div className={styles.note}>{p.note}</div>
      </div>
    );
  }
  return (
    <div className={styles.body}>
      <div className={styles.kind}>Computed here from</div>
      <ul className={styles.inputs}>
        {p.inputs.map((inp, i) => (
          <li key={i}>
            {inp.source ? <Link href={sourceUrl(inp.source)}>{inp.label}</Link> : inp.label}
          </li>
        ))}
      </ul>
      <div className={styles.note}>{p.formula}</div>
    </div>
  );
}
