import styles from "./StatusBadge.module.css";

interface Props {
  status: string;
  label?: string;
}

/** Icon + text in the status color, no pill background (BRIEF 5.8). */
export function StatusBadge({ status, label }: Props) {
  const text =
    label ??
    (status === "verified" ? "Verified" :
     status === "partial" ? "Partly verified" : "Not verified");
  const cls =
    status === "verified" ? styles.ok :
    status === "partial" ? styles.partial : styles.flag;
  const glyph = status === "verified" ? "✓" : status === "partial" ? "◐" : "⚑";
  return (
    <span className={`${styles.badge} ${cls}`}>
      <span aria-hidden className={styles.glyph}>{glyph}</span> {text}
    </span>
  );
}
