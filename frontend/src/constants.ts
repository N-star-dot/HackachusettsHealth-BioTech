export const APP_NAME = "Lab Planner";

export const EXAMPLES = [
  "HER2 kinase inhibitors in breast cancer",
  "p38 MAPK inhibitors in inflammation",
  "JAK inhibitors in autoimmune disease",
] as const;

export const HOW_IT_WORKS = [
  "Checks how crowded the topic is in OpenAlex.",
  "Designs a first dose-response experiment from published ChEMBL measurements and checks every citation.",
  "Runs the protocol in the Opentrons simulator.",
  "Simulates the experiment many times with real-world noise to show how far off the answer could be.",
] as const;
