// Recorded runs (BRIEF 3.6): raw RunResponse JSON captured from the real backend, served
// from public/demo/, so the dashboard renders with the backend off.
import type { RunResponse } from "./types";

export interface RecordedIndexEntry {
  file: string;
  question: string;
  recorded_at: string;
  commit: string;
}

export async function loadRecordedIndex(): Promise<RecordedIndexEntry[]> {
  try {
    const res = await fetch("/demo/index.json");
    if (!res.ok) return [];
    return (await res.json()) as RecordedIndexEntry[];
  } catch {
    return [];
  }
}

export async function loadRecordedRun(file: string): Promise<RunResponse | null> {
  try {
    const res = await fetch(`/demo/${file}`);
    if (!res.ok) return null;
    return (await res.json()) as RunResponse;
  } catch {
    return null;
  }
}
