import { useRef, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import type { Provenance } from "./provenance";
import { KIND_LABEL, sourceUrl } from "../../lib/provenance";
import styles from "./Num.module.css";

interface Props {
  value: string;              // already-formatted text
  provenance: Provenance;
  className?: string;
}

/** True on pointer devices with hover (not touch). Hover-to-open is only enabled there;
 *  click and keyboard always work. */
function canHover(): boolean {
  return typeof window !== "undefined"
    && typeof window.matchMedia === "function"
    && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

/** Every number on screen renders through <Num> with a source (BRIEF 5.15 / rule R0.1).
 *  A dotted underline opens a provenance popover on click, Enter, or (on pointer devices)
 *  hover after 300 ms (W1.7). In dev, a missing provenance is a bug (magenta outline +
 *  console warning) — caught by a test. */
export function Num({ value, provenance, className }: Props) {
  if (import.meta.env.DEV && !provenance) {
    // eslint-disable-next-line no-console
    console.warn("<Num> rendered without provenance:", value);
  }
  const [open, setOpen] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearHover = () => {
    if (hoverTimer.current) { clearTimeout(hoverTimer.current); hoverTimer.current = null; }
  };
  const onEnter = () => {
    if (!canHover()) return;
    clearHover();
    hoverTimer.current = setTimeout(() => setOpen(true), 300);
  };
  const onLeave = () => {
    clearHover();
    if (canHover()) setOpen(false);
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={`${styles.num} num ${className ?? ""}`}
          data-num
          data-provenance={provenance.kind}
          onPointerEnter={onEnter}
          onPointerLeave={onLeave}
        >
          {value}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className={styles.pop}
          sideOffset={6}
          onPointerEnter={clearHover}
          onPointerLeave={onLeave}
          // keep hover-opened popovers from stealing focus
          onOpenAutoFocus={(e) => { if (canHover()) e.preventDefault(); }}
        >
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
