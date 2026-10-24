// The mock/live-API toggle, persisted to localStorage so a reload keeps it.

import { useEffect, useState } from "react";
import type { DataMode } from "../api";

const STORAGE_KEY = "dashboard.mode";

function initialMode(): DataMode {
  try {
    return localStorage.getItem(STORAGE_KEY) === "api" ? "api" : "mock";
  } catch {
    return "mock";
  }
}

export function useDataMode(): [DataMode, (m: DataMode) => void] {
  const [mode, setMode] = useState<DataMode>(initialMode);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* storage unavailable; the toggle just won't persist */
    }
  }, [mode]);

  return [mode, setMode];
}
