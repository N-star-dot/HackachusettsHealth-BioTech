// Motion constants (BRIEF section 7). The run reveal is the only automatic choreography;
// everything else answers a user action.
export const DUR = { fast: 0.12, base: 0.22, travel: 0.35 } as const;
export const EASE = [0.2, 0, 0, 1] as const;
export const SPRING = { stiffness: 380, damping: 36 } as const;

export const REVEAL_STAGGER = 0.35; // seconds between stage reveals
