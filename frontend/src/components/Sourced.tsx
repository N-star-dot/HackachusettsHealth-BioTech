import { useId, useState, type ReactNode } from "react";
import { sourceHref, sourceLabel } from "../format";
import type { Source } from "../types";

interface Props {
  /** One or more provenance tags. A number with none (and no `derived`) is flagged in red. */
  source?: Source | Source[] | null;
  /** For numbers the dashboard computes itself: says how. */
  derived?: string;
  children: ReactNode;
  /** Extra line under the source, e.g. a model version. */
  note?: string;
  className?: string;
}

/**
 * Wraps a number so hovering or focusing it shows where it came from.
 * This is the dashboard's trust feature: every displayed number goes through here.
 */
export function Sourced({ source, derived, children, note, className }: Props) {
  const [open, setOpen] = useState(false);
  const tipId = useId();
  const sources = source ? (Array.isArray(source) ? source : [source]) : [];
  const missing = sources.length === 0 && !derived;

  return (
    <span
      className={`sourced${missing ? " sourced--missing" : ""}${className ? ` ${className}` : ""}`}
      tabIndex={0}
      aria-describedby={tipId}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      {children}
      <span id={tipId} role="tooltip" className="tip" data-open={open || undefined}>
        <span className="tip__head">{missing ? "No source" : derived && !sources.length ? "Computed here" : "Source"}</span>
        {missing && <span className="tip__line">This number has no provenance tag.</span>}
        {derived && <span className="tip__line">{derived}</span>}
        {sources.map((s, i) => {
          const href = sourceHref(s);
          return (
            <span key={i} className="tip__line">
              <span className="tip__type">{sourceLabel(s)}</span>{" "}
              {href ? (
                <a href={href} target="_blank" rel="noreferrer">
                  {s.id}
                </a>
              ) : (
                <span className="mono">{s.id}</span>
              )}
            </span>
          );
        })}
        {note && <span className="tip__line tip__note">{note}</span>}
      </span>
    </span>
  );
}
