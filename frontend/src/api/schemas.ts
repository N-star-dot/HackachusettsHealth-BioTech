// Loose zod validation at the boundary (BRIEF 3.4). Objects are loose: unknown keys pass
// (zod strips them). On failure we surface the failing path in a dev panel.
import { z } from "zod";

const source = z.object({
  type: z.string(),
  id: z.string(),
  url: z.string().nullish(),
});

const safetyGate = z.object({
  pass: z.boolean().optional(),
  passed: z.boolean().optional(),
  reasons: z.array(z.string()),
});

const topicReport = z.object({
  query: z.string(),
  topic: z.object({ openalex_id: z.string(), name: z.string() }),
  counts_by_year: z.array(
    z.object({ year: z.number(), works: z.number(), source }),
  ),
  momentum: z.object({ p_growth: z.number(), model: z.string() }),
  neighbors: z.array(z.any()),
  matrix: z.object({ total: z.number(), weights: z.record(z.string(), z.number()) }).passthrough(),
  safety: safetyGate,
  offline: z.boolean().optional(),
});

const simResult = z.object({
  design_id: z.string(),
  protocol_file: z.string(),
  simulator: z.object({
    pass: z.boolean().optional(),
    passed: z.boolean().optional(),
    error: z.string().nullable(),
    log_lines: z.number(),
    seconds: z.number(),
    opentrons_version: z.string(),
  }),
  cost: z.object({
    tips: z.number(),
    compound_uL: z.number(),
    plates: z.number(),
    robot_steps: z.number(),
    source: source.nullish(),
  }),
  steps: z.array(z.any()),
  deck: z.array(z.any()).optional(),
});

const uncertaintyReport = z.object({
  design_id: z.string(),
  label: z.string(),
  runs: z.number(),
  seed: z.number(),
  noise: z.object({}).passthrough(),
  fold_error: z.object({ median: z.number(), p90: z.number() }),
  outside_range_share: z.number(),
  failed_fit_share: z.number(),
  calibration: z.object({ coverage_90: z.number(), pairs: z.number() }),
  next_experiments: z.array(z.any()),
  samples: z.any().nullish(),
  curve: z.any().nullish(),
});

export const runResponse = z.object({
  run_id: z.string(),
  blocked: z.boolean(),
  status: z.string().optional(),
  pair: z.any().nullish(),
  topic: topicReport.nullable(),
  design: z.any().nullable(),
  sim: simResult.nullable(),
  uncertainty: uncertaintyReport.nullable(),
});

export const runRecord = runResponse.extend({
  meta: z.object({
    run_id: z.string(),
    query: z.string(),
    created_at: z.string(),
    status: z.string(),
    error: z.string().nullish(),
  }),
});

/** Validate, returning either the parsed value or the first failing path for the dev panel. */
export function safeParse<T>(schema: z.ZodType<T>, data: unknown):
  | { ok: true; value: T }
  | { ok: false; path: string } {
  const res = schema.safeParse(data);
  if (res.success) return { ok: true, value: res.data };
  const issue = res.error.issues[0];
  return { ok: false, path: issue ? issue.path.join(".") || "(root)" : "(unknown)" };
}
