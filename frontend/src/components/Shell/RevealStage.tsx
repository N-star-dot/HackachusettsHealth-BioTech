import { motion, useReducedMotion } from "motion/react";
import { DUR, EASE, REVEAL_STAGGER } from "../../design/motion";

interface Props {
  order: number; // 0-based stage order
  children: React.ReactNode;
}

/** The run reveal (BRIEF 7.1): the only automatic choreography. Stages fade/rise in order,
 *  350 ms apart. With reduced motion, content appears at once with a short opacity fade. */
export function RevealStage({ order, children }: Props) {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
        {children}
      </motion.div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DUR.travel, ease: EASE, delay: order * REVEAL_STAGGER }}
    >
      {children}
    </motion.div>
  );
}
