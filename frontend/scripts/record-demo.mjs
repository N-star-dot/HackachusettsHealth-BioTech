// Capture raw RunResponse JSON from a running backend into public/demo/ (BRIEF 3.6).
// Usage: node scripts/record-demo.mjs   (backend must be up on 127.0.0.1:8000)
import { writeFileSync, mkdirSync } from "node:fs";
import { execSync } from "node:child_process";

const BASE = process.env.VITE_API_BASE || "http://127.0.0.1:8000";
const QUESTIONS = [
  "HER2 kinase inhibitors in breast cancer",
  "p38 MAPK inhibitors in inflammation",
  "JAK inhibitors in autoimmune disease",
];

let commit = "unknown";
try { commit = execSync("git rev-parse --short HEAD").toString().trim(); } catch {}

mkdirSync("public/demo", { recursive: true });
const index = [];
for (let i = 0; i < QUESTIONS.length; i++) {
  const q = QUESTIONS[i];
  const res = await fetch(`${BASE}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: q, runs: 1000 }),
  });
  if (!res.ok) { console.error(`FAILED ${q}: ${res.status}`); continue; }
  const body = await res.json();
  const file = `run-${i + 1}.json`;
  writeFileSync(`public/demo/${file}`, JSON.stringify(body, null, 2));
  index.push({ file, question: q, recorded_at: new Date().toISOString(), commit });
  console.log(`recorded ${file}: ${q}`);
}
writeFileSync("public/demo/index.json", JSON.stringify(index, null, 2));
console.log(`wrote index.json (${index.length} runs)`);
