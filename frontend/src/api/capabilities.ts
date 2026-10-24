// Capability detection (BRIEF 3.3). Read /openapi.json once + optional response fields
// to derive feature flags. Every feature has a fallback; none blocks P0.
import { api } from "./client";

export interface Capabilities {
  typedResponses: boolean;   // components.schemas.RunResponse
  pairPicker: boolean;       // /api/pairs
  whatIfSimulate: boolean;   // /api/simulate
  protocolViewer: boolean;   // /api/protocol/{name}
  metrics: boolean;          // /api/metrics
  evidence: boolean;         // /api/evidence/{id}
  asyncRun: boolean;         // RunRequest.mode
}

const EMPTY: Capabilities = {
  typedResponses: false,
  pairPicker: false,
  whatIfSimulate: false,
  protocolViewer: false,
  metrics: false,
  evidence: false,
  asyncRun: false,
};

export async function detectCapabilities(): Promise<Capabilities> {
  try {
    const spec = await api.get<any>("/openapi.json");
    const paths: Record<string, unknown> = spec.paths ?? {};
    const schemas: Record<string, unknown> = spec.components?.schemas ?? {};
    const runReqProps =
      (schemas.RunRequest as any)?.properties ?? {};
    return {
      typedResponses: "RunResponse" in schemas,
      pairPicker: "/api/pairs" in paths || "compound_chembl_id" in runReqProps,
      whatIfSimulate: "/api/simulate" in paths,
      protocolViewer: Object.keys(paths).some((p) => p.startsWith("/api/protocol/")),
      metrics: "/api/metrics" in paths,
      evidence: Object.keys(paths).some((p) => p.startsWith("/api/evidence/")),
      asyncRun: "mode" in runReqProps,
    };
  } catch {
    return EMPTY; // offline / no server -> everything falls back
  }
}
