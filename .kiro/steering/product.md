# Product

A researcher types a topic and gets three things back:
1. **Where the open questions are** — momentum + novelty scoring from real publication data.
2. **A ready-to-run robot protocol** for a first dose-response experiment on an Opentrons Flex.
3. **An honest estimate of real-world noise** — how much lab and robot error will blur the answer.

## Who it is for
Student researchers, early-stage labs, and young biotech companies in Massachusetts
that pick experiments without a data science team. A badly designed experiment wastes
compound, robot time, and weeks; ideal simulations hide that risk.

## Non-negotiable product rules
- **Every number carries a source**, or sits inside a block explicitly labelled `simulated`.
- **Only stage-4 assay readouts are simulated.** Everything else is real data.
- **Safety is a gate, not an axis** — it runs before any scoring and can block a topic outright.
- **We never claim to be first.** Related work (Google co-scientist, CMU Coscientist 2023)
  is acknowledged in the first 20 seconds of the pitch. Our edge: free, open, student-scale,
  every number traceable, and the simulation checks its own uncertainty against real data.

## What is real vs simulated
| Output | Real or simulated | Source shown |
|--------|-------------------|--------------|
| Topic counts & trends | Real (OpenAlex, PubMed) | source id on hover |
| Citations in the design | Real (each PMID checked) | verified badge / red flag |
| Starting IC50 guess | Real (ChEMBL) | ChEMBL activity ids |
| Protocol runs? | Real (Opentrons simulator) | pass / exact error + line |
| Pipetting error | Real (Opentrons specs) | link to spec table |
| Assay readouts & recovered IC50 | **Simulated**, noise from real data | labelled "simulated, seed N" |

IC50 = concentration at which a compound cuts its target's activity in half. Lower = more potent.
