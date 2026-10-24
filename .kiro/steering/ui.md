---
inclusion: fileMatch
fileMatchPattern: "frontend/**"
---
# Lab Planner UI rules

Full spec: frontend/BRIEF.md. These rules apply to every file under frontend/.

## Honesty
- Every number renders through <Num> with a source, simulated or derived provenance. No bare numbers in JSX.
- Never invent data, progress percentages or placeholder charts. Missing data gets one plain sentence saying what is missing.
- Model-written text is never shown as verified. Only RationaleItem.status decides a badge.
- The replay always says it replays the Opentrons simulator run.
- No third-party logos.
- Backend quirks are handled in src/api/normalize.ts only.

## Look
- Colors come from src/design/tokens.css only. No raw hex in components.
- Archivo Variable everywhere, width by role (75% labels, 100% UI, 112-118% display numbers). Newsreader Variable only for quotes from papers. Monospace only in the protocol viewer.
- Tabular numerals for every number.
- Radius by role: 2px inputs, 6px buttons, slots, popovers, 14px deck. Shadows only on popovers and a dragged thumb.
- Pink and blue are data colors for target activity. Never use them for UI chrome.

## Banned
Cream with terracotta. Near-black with acid green. Identical rounded cards with the same soft shadow. Gradient washes. Glassmorphism. All-caps or letter-spaced labels. Middle-dot meta strings. Em dashes in UI copy. Monospace data labels. Arrows in button text. Emoji. Sparkle icons. "AI-powered". Fade-and-slide-up on every section. Hover lifts on panels. Parallax. Radar charts, gauges, donuts. One accented word in a headline. Centered hero text. Skeleton shimmer.

## Copy
Sentence case. Plain verbs. Buttons name the action. Errors say what happened and what to do next. No exclamation marks.

## Motion
- The run reveal (BRIEF 7.1) is the only automatic choreography. Everything else answers a user action.
- 120 ms fast, 220 ms base, 350 ms travel. Springs stiffness 380, damping 36.
- prefers-reduced-motion: no travel, instant state changes, at most a 150 ms fade.

## Accessibility
Visible focus (2px ink outline, 2px offset). Color never carries meaning alone. Every control works by keyboard. Charts have text summaries. No horizontal scroll at 390px.
