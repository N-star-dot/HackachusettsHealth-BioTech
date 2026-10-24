import styles from "./DeckPlaceholder.module.css";

/** Minimal idle deck schematic for the start screen (P0-1). The full deck + replay
 *  arrive in P0-9 / P1-1. Slots are drawn, not logos. */
export function DeckPlaceholder() {
  const slots = ["A1", "A2", "A3 bin", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "D3"];
  return (
    <div className={styles.bench}>
      <div className={styles.deck} aria-label="Empty Opentrons Flex deck">
        {slots.map((s) => (
          <div key={s} className={styles.slot}>
            <span className={styles.slotLabel}>{s}</span>
          </div>
        ))}
      </div>
      <p className={styles.caption}>Your experiment will be laid out here.</p>
    </div>
  );
}
