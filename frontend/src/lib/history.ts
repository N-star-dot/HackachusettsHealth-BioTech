// Run history in localStorage (BRIEF 5.14), guarded against storage errors.
export interface HistoryEntry {
  runId: string;
  question: string;
  topicName: string;
  viability: number;
  p90: number;
  at: number;
}

const KEY = "labplanner.history";

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function pushHistory(entry: HistoryEntry): void {
  try {
    const list = loadHistory().filter((e) => e.runId !== entry.runId);
    list.unshift(entry);
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, 20)));
  } catch {
    /* storage full / disabled — history is best-effort */
  }
}
