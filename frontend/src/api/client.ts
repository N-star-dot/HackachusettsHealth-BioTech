// One fetch wrapper (BRIEF 3.4). Base URL from VITE_API_BASE or "" (proxy). Per-call
// AbortController timeouts: run 90s, uncertainty 30s, simulate 15s, else 10s.

const BASE = import.meta.env.VITE_API_BASE || "";

export const TIMEOUTS = {
  run: 90_000,
  uncertainty: 30_000,
  simulate: 15_000,
  default: 10_000,
} as const;

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  opts: { method?: string; body?: unknown; timeout?: number; signal?: AbortSignal } = {},
): Promise<T> {
  const { method = "GET", body, timeout = TIMEOUTS.default, signal } = opts;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  // chain an external signal (what-if cancellation) onto our timeout controller
  if (signal) signal.addEventListener("abort", () => ctrl.abort(), { once: true });

  try {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const detail = (data && (data.detail ?? data)) ?? res.statusText;
      throw new ApiError(res.status, detail, `${res.status} ${path}`);
    }
    return data as T;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get: <T>(path: string, timeout?: number) => request<T>(path, { timeout }),
  post: <T>(path: string, body: unknown, timeout?: number, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", body, timeout, signal }),
  baseUrl: () => BASE || "(same origin via proxy)",
};
